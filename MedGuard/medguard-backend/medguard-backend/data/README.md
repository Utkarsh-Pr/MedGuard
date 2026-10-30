# Medicine-strip dataset contract

The classifier is a **closed-set** model: every image must be assigned to one
of the catalog labels or to `unknown`. Do not add scraped images unless their
license or permission is recorded in `sources.csv`.

## Layout

```
data/
  manifests/all.csv
  manifests/train.csv
  manifests/validation.csv
  manifests/test.csv
  manifests/unknown_test.csv
```

The generated manifests use `path,label,source_filename,capture_group`.
`capture_group` is derived from the filename before a Roboflow `.rf.<hash>`
suffix. Splits must be made by capture group, never randomly by image.

For every catalog item collect photos across distances, rotations, backgrounds,
glare, low/bright lighting, package revisions, and partially occluded text.
The unknown set must contain strips and non-strip images not represented by the
catalog. It is used to calibrate the confidence/margin gate to a maximum 3%
false acceptance rate.

For the current Pharmassist data, run:

```powershell
python scripts/build_dataset_manifests.py "..\\..\\Pharmassist Dataset\\raw" data/manifests
```
