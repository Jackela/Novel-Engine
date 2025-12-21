# Legal Notice

## Non-Affiliation Disclaimer

This software is not affiliated with or endorsed by any commercial entity, publisher, or rights holder of any intellectual property (including, but not limited to, Games Workshop Group PLC). This is an independent, non-commercial project developed for educational and research purposes.

## Copyright and Fair Use

This software contains no copyrighted content and is provided under fair use provisions. All original content is the work of the contributors and is provided under the project's license terms.

## Fan Mode Compliance

When operating in "fan" mode, users must ensure compliance with the following restrictions:

### Usage Restrictions
- **Non-Commercial Use Only**: Fan mode content may not be used for commercial purposes
- **Local Distribution Only**: Content generated in fan mode must not be distributed beyond local usage
- **Compliance Documentation**: Users must maintain appropriate compliance documentation in `private/registry.yaml`

### Required Configuration
Fan mode requires a valid `private/registry.yaml` file containing:
```yaml
sources: []  # Your source material definitions

compliance:
  non_commercial: true
  distribution: "local_only"
```

### Legal Responsibility
Users are responsible for ensuring their use of fan mode complies with applicable copyright laws in their jurisdiction. The software provides technical safeguards but users bear ultimate legal responsibility.

## DMCA and Content Removal

If you believe this software infringes your intellectual property rights, please contact the project maintainers with:

1. Identification of the copyrighted work claimed to be infringed
2. Specific identification of the allegedly infringing material
3. Contact information for the complaining party
4. A statement of good faith belief that use is not authorized
5. A statement of accuracy made under penalty of perjury
6. electronic or physical signature of the copyright owner or authorized representative

## Disclaimer of Warranties

This software is provided "as is" without warranty of any kind, either expressed or implied, including but not limited to the implied warranties of merchantability and fitness for a particular purpose.

## Limitation of Liability

In no event shall the authors or copyright holders be liable for any claim, damages, or other liability, whether in an action of contract, tort, or otherwise, arising from, out of, or in connection with the software or the use or other dealings in the software.

---

*Last Updated: 2025-08-11*

## Trademarks and Third-Party Assets

- Do not submit third-party copyrighted text, images, rules, or trademarked terms to the public repository.
- IP/trademark hygiene is enforced by CI tooling (see `scripts/term_guard.py`) using the banned-term list in `settings.yaml`.
