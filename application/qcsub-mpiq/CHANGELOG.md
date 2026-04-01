## [0.2025.v0-1.0] - 2025-01-23

### Authors

- Ara Ghukasyan <38226926+araghukas@users.noreply.github.com>
- Casey Jao <casey@agnostiq.ai>


### Changed

- Updated Slurm plugin docs to note possible SSH limitation
- Updated Slurm plugin docs to remove `sshproxy` section
- API base endpoint is now configurable from an environment variable
- Removed unused lattice attributes to reduce asset uploads

### Fixed

- Improved handling of Covalent version mismatches between client and
  executor environments

### Removed

- Removed obsolete `migrate-pickled-result-object` command

### Operations

- Allow installing a specific commit sha to ease testing