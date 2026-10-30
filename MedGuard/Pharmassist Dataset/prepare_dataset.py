import random
import shutil
from pathlib import Path
from PIL import Image
from collections import Counter


# ============================================================
# CONFIGURATION
# ============================================================

# Folder containing the 53 medicine folders
RAW_DIR = Path("raw")

# Where the processed dataset will be created
OUTPUT_DIR = Path("processed")

# Train / validation / test split
TRAIN_RATIO = 0.80
VAL_RATIO = 0.10
TEST_RATIO = 0.10

# Reproducible random split
RANDOM_SEED = 42

# Supported image formats
IMAGE_EXTENSIONS = {
    ".jpg",
    ".jpeg",
    ".png",
    ".webp",
    ".bmp"
}


# ============================================================
# CHECK RATIOS
# ============================================================

assert abs(
    TRAIN_RATIO + VAL_RATIO + TEST_RATIO - 1.0
) < 1e-6


# ============================================================
# SET RANDOM SEED
# ============================================================

random.seed(RANDOM_SEED)


# ============================================================
# CHECK RAW DIRECTORY
# ============================================================

if not RAW_DIR.exists():

    print("ERROR: 'raw' folder was not found.")

    print(
        "Make sure this script is inside "
        "the main Pharmassist Dataset folder."
    )

    exit()


# ============================================================
# FIND MEDICINE CLASSES
# ============================================================

classes = sorted(
    [
        folder
        for folder in RAW_DIR.iterdir()
        if folder.is_dir()
    ],
    key=lambda x: x.name.lower()
)


print("=" * 60)
print("PHARMASSIST DATASET PREPARATION")
print("=" * 60)

print(
    f"\nMedicine classes found: {len(classes)}"
)


# ============================================================
# EXPECT 53 CLASSES
# ============================================================

if len(classes) != 53:

    print(
        f"\nWARNING: Expected 53 classes, "
        f"but found {len(classes)}."
    )

else:

    print("✓ Found all 53 classes.")


# ============================================================
# CREATE OUTPUT DIRECTORIES
# ============================================================

for split in [
    "train",
    "val",
    "test"
]:

    for class_folder in classes:

        output_class_folder = (
            OUTPUT_DIR /
            split /
            class_folder.name
        )

        output_class_folder.mkdir(
            parents=True,
            exist_ok=True
        )


# ============================================================
# PROCESS EACH CLASS
# ============================================================

total_images = 0
total_valid = 0
total_corrupt = 0

split_counter = Counter()


for class_folder in classes:

    class_name = class_folder.name

    print(
        f"\nProcessing: {class_name}"
    )

    # --------------------------------------------------------
    # Find images
    # --------------------------------------------------------

    images = [
        file
        for file in class_folder.iterdir()
        if (
            file.is_file()
            and
            file.suffix.lower()
            in IMAGE_EXTENSIONS
        )
    ]

    total_images += len(images)

    print(
        f"  Images found: {len(images)}"
    )

    # --------------------------------------------------------
    # Check image integrity
    # --------------------------------------------------------

    valid_images = []

    for image_path in images:

        try:

            with Image.open(image_path) as img:

                # Verify image
                img.verify()

            valid_images.append(
                image_path
            )

        except Exception:

            print(
                f"  WARNING: Corrupt image: "
                f"{image_path.name}"
            )

            total_corrupt += 1

    total_valid += len(valid_images)

    # --------------------------------------------------------
    # Shuffle
    # --------------------------------------------------------

    random.shuffle(valid_images)

    # --------------------------------------------------------
    # Calculate split sizes
    # --------------------------------------------------------

    n = len(valid_images)

    train_count = int(
        n * TRAIN_RATIO
    )

    val_count = int(
        n * VAL_RATIO
    )

    # Remaining images go to test
    test_count = (
        n
        - train_count
        - val_count
    )

    train_images = (
        valid_images[
            :train_count
        ]
    )

    val_images = (
        valid_images[
            train_count:
            train_count + val_count
        ]
    )

    test_images = (
        valid_images[
            train_count + val_count:
        ]
    )

    # --------------------------------------------------------
    # Copy files
    # --------------------------------------------------------

    splits = {
        "train": train_images,
        "val": val_images,
        "test": test_images
    }

    for split_name, split_images in splits.items():

        destination = (
            OUTPUT_DIR /
            split_name /
            class_name
        )

        for image_path in split_images:

            destination_file = (
                destination /
                image_path.name
            )

            shutil.copy2(
                image_path,
                destination_file
            )

        split_counter[
            split_name
        ] += len(split_images)

    print(
        f"  Train: {len(train_images)}"
    )

    print(
        f"  Validation: {len(val_images)}"
    )

    print(
        f"  Test: {len(test_images)}"
    )


# ============================================================
# FINAL SUMMARY
# ============================================================

print("\n")
print("=" * 60)
print("DATASET PREPARATION COMPLETE")
print("=" * 60)

print(
    f"\nOriginal images found: "
    f"{total_images}"
)

print(
    f"Valid images: "
    f"{total_valid}"
)

print(
    f"Corrupt images: "
    f"{total_corrupt}"
)

print("\nFinal split:")

print(
    f"Train: "
    f"{split_counter['train']}"
)

print(
    f"Validation: "
    f"{split_counter['val']}"
)

print(
    f"Test: "
    f"{split_counter['test']}"
)

print(
    f"\nOutput directory:"
)

print(
    OUTPUT_DIR.resolve()
)

print("\nDone!")