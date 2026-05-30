You are helping prepare a small machine-learning training-data bundle under `/home/user/ml_data_prep`.

The source data is already present as a compressed tar archive at:

`/home/user/ml_data_prep/raw/image_labels_batch.tar.gz`

Create the final compressed deliverable for the training job at:

`/home/user/ml_data_prep/deliverables/training_data_ready.zip`

The final ZIP archive must contain exactly these three files at the top level of the archive, with no parent directory entries and no extra files:

- `images/img_001.txt`
- `images/img_002.txt`
- `labels/labels.csv`

Do not modify the original archive. Extract the source archive into a working directory of your choice under `/home/user/ml_data_prep/work`, then package only the required `images` and `labels` contents into the ZIP file above.

After creating the ZIP archive, verify it and write a plain-text verification log at:

`/home/user/ml_data_prep/deliverables/verification.log`

The automated checker will inspect this log, so use exactly this format:

- Line 1: `archive=/home/user/ml_data_prep/deliverables/training_data_ready.zip`
- Line 2: `status=verified`
- Line 3: `entries=3`

Only write `status=verified` after you have checked that the ZIP archive exists and contains exactly the three required file paths listed above. Some archive commands may complete with little or no terminal output, so do not stop just because a command is quiet; explicitly inspect the ZIP contents before writing the verification log.
