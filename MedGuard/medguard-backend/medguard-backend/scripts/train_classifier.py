"""Fine-tune MobileNetV3-Small and export a CPU ONNX classifier."""
import argparse
import copy
import csv
import json
from collections import Counter
from pathlib import Path

import torch
from PIL import Image
from sklearn.metrics import classification_report, confusion_matrix
from torch import nn
from torch.utils.data import DataLoader, Dataset, WeightedRandomSampler
from torchvision import models, transforms


class ManifestDataset(Dataset):
    def __init__(self, manifest_path, label_to_index, transform):
        self.rows = list(csv.DictReader(Path(manifest_path).open(encoding="utf-8", newline="")))
        self.label_to_index, self.transform = label_to_index, transform
    def __len__(self): return len(self.rows)
    def __getitem__(self, index):
        row = self.rows[index]
        with Image.open(row["path"]) as image:
            return self.transform(image.convert("RGB")), self.label_to_index[row["label"]]


def evaluate(model, loader, device, labels):
    model.eval(); predictions, targets = [], []
    with torch.inference_mode():
        for images, batch_targets in loader:
            predictions.extend(model(images.to(device)).argmax(1).cpu().tolist()); targets.extend(batch_targets.tolist())
    report = classification_report(targets, predictions, labels=range(len(labels)), target_names=labels, output_dict=True, zero_division=0)
    return report, confusion_matrix(targets, predictions, labels=range(len(labels))).tolist()


def main(train_manifest, validation_manifest, test_manifest, output_dir="models", epochs=16, batch_size=24):
    train_rows = list(csv.DictReader(Path(train_manifest).open(encoding="utf-8", newline="")))
    labels = sorted({row["label"] for row in train_rows}, key=str.lower)
    label_to_index = {label: index for index, label in enumerate(labels)}
    device = "cuda" if torch.cuda.is_available() else "cpu"
    normalize = transforms.Normalize([.485, .456, .406], [.229, .224, .225])
    train_transform = transforms.Compose([transforms.Resize((256, 256)), transforms.RandomResizedCrop(224, scale=(.70, 1.0)), transforms.RandomRotation(20), transforms.RandomPerspective(.15, p=.35), transforms.ColorJitter(.30, .30, .18, .08), transforms.GaussianBlur(3, sigma=(.1, 1.2)), transforms.ToTensor(), normalize])
    evaluation_transform = transforms.Compose([transforms.Resize((224, 224)), transforms.ToTensor(), normalize])
    train_dataset = ManifestDataset(train_manifest, label_to_index, train_transform)
    validation_dataset = ManifestDataset(validation_manifest, label_to_index, evaluation_transform)
    test_dataset = ManifestDataset(test_manifest, label_to_index, evaluation_transform)
    counts = Counter(row["label"] for row in train_rows)
    weights = [1 / counts[row["label"]] for row in train_dataset.rows]
    train_loader = DataLoader(train_dataset, batch_size=batch_size, sampler=WeightedRandomSampler(weights, len(weights), replacement=True), num_workers=0)
    validation_loader = DataLoader(validation_dataset, batch_size=batch_size, shuffle=False, num_workers=0)
    test_loader = DataLoader(test_dataset, batch_size=batch_size, shuffle=False, num_workers=0)
    model = models.mobilenet_v3_small(weights=models.MobileNet_V3_Small_Weights.DEFAULT)
    model.classifier[3] = nn.Linear(model.classifier[3].in_features, len(labels)); model.to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=2e-4, weight_decay=1e-4)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=epochs)
    loss_function = nn.CrossEntropyLoss(); best_accuracy, best_state = -1.0, None
    for epoch in range(1, epochs + 1):
        model.train(); total_loss = 0.0
        for images, targets in train_loader:
            optimizer.zero_grad(set_to_none=True)
            loss = loss_function(model(images.to(device)), targets.to(device))
            loss.backward(); optimizer.step(); total_loss += loss.item() * len(targets)
        validation_report, _ = evaluate(model, validation_loader, device, labels)
        validation_accuracy = validation_report["accuracy"]
        print(f"epoch={epoch} loss={total_loss / len(train_dataset):.4f} validation_accuracy={validation_accuracy:.4f}")
        if validation_accuracy > best_accuracy: best_accuracy, best_state = validation_accuracy, copy.deepcopy(model.state_dict())
        scheduler.step()
    model.load_state_dict(best_state); model.eval().cpu()
    validation_report, _ = evaluate(model, validation_loader, "cpu", labels)
    test_report, test_confusion = evaluate(model, test_loader, "cpu", labels)
    output = Path(output_dir); output.mkdir(parents=True, exist_ok=True)
    torch.save({"state_dict": model.state_dict(), "labels": labels}, output / "medicine_classifier.pt")
    torch.onnx.export(model, torch.randn(1, 3, 224, 224), output / "medicine_classifier.onnx", input_names=["image"], output_names=["logits"], dynamic_axes={"image": {0: "batch"}, "logits": {0: "batch"}}, opset_version=17)
    (output / "labels.json").write_text(json.dumps(labels, indent=2), encoding="utf-8")
    (output / "training_report.json").write_text(json.dumps({"catalog_size": len(labels), "device": device, "best_validation_accuracy": best_accuracy, "validation": validation_report, "test": test_report, "test_confusion_matrix": test_confusion}, indent=2), encoding="utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("train_manifest"); parser.add_argument("validation_manifest"); parser.add_argument("test_manifest")
    parser.add_argument("--output-dir", default="models"); parser.add_argument("--epochs", type=int, default=16); parser.add_argument("--batch-size", type=int, default=24)
    args = parser.parse_args()
    main(args.train_manifest, args.validation_manifest, args.test_manifest, args.output_dir, args.epochs, args.batch_size)
