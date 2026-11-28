# Core fork releases

- Core builds from this fork report `+fork.xuhuanhello.N` in both `hc --version` and the protocol handshake. The App uses that version to distinguish a Core that is already running from the executable it found.
- The two archive URLs are tied to the GitHub release tag and verified against the manifest's SHA-256 before extraction. Use an isolated session and state directories to verify a Core update.
- An existing Mac bundle must select the bundled executable from release archives even when it is installed outside the home directory. The updater cannot replace a bundle with a standalone executable.
- Keep macOS test socket paths short. The Core test harness accepts `HC_TEST_TMPDIR=/tmp` and creates its own isolated subdirectories.
