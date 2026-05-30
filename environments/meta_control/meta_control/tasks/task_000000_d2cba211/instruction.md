I’m maintaining a mobile CI pipeline and need a small release-summary artifact generated from an INI file.

    The input file is already present at:

    /home/user/mobile-pipeline.ini

    It contains multiple build profiles. The only profile that matters is the one named by the top-level key active_profile in the [pipeline] section. Do not summarize the first profile in the file unless it is actually the active one.

    Please create this output file:

    /home/user/build/release-summary.tsv

    Create /home/user/build if it does not already exist.

    The output file must contain exactly two lines:

    1. A header line with these tab-separated column names, in this exact order:

    profile	applicationId	versionName	versionCode	track

    2. One tab-separated data line for the active profile only. The fields must be:
    - the active profile name
    - applicationId from that profile’s section
    - versionName from that profile’s section
    - versionCode from that profile’s section
    - track from that profile’s section

    The relevant profile section is named using this format:

    [profile.&lt;active_profile&gt;]

    For example, if active_profile is qa, then the values must come from [profile.qa].

    Important parsing details:
    - Ignore blank lines.
    - Ignore full-line comments beginning with # or ;.
    - Preserve dots and hyphens inside values.
    - Do not include surrounding whitespace around keys or values.
    - Only use values from the active profile section, not from any other profile section.

    Before finishing, verify the file exists and that it has exactly two lines. The automated check will inspect /home/user/build/release-summary.tsv directly, so the exact tab-separated format matters.
