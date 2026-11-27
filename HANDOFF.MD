# Core fork releases

- Core builds from this fork report `+fork.xuhuanhello.N` in both `hc --version` and the protocol handshake. The App uses that version to distinguish a Core that is already running from the executable it found.
- The two archive URLs are tied to the GitHub release tag and verified against the manifest's SHA-256 before extraction. Use an isolated session and state directories to verify a Core update.
