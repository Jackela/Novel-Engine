# Codex: Legal & Compliance (LEGAL.md)
*Document Version: 1.2*
*Last Updated: 2025-08-11*

This document outlines the legal and compliance framework for the Novel Engine project.

## 1. Non-Affiliation Disclaimer

This project, the "Novel Engine," is an independent, non-commercial research framework. It is not affiliated with, endorsed, sponsored, or approved by Games Workshop Group PLC or any of its affiliates. All trademarks, service marks, names, and logos associated with the Novel Engine 40,000 universe are the property of their respective owners.

## 2. Usage Boundaries & Non-Commercial Use

This project is provided strictly for non-commercial, educational, and research purposes.
-   **Prohibited Uses:** You may not sell, license, or lease the software. You may not use the software to generate revenue in any way, including but not limited to: paid access, advertising, donations that unlock features, or selling generated content.
-   **No Redistribution of Third-Party Assets:** The project repository and any distributed packages **do not** contain any third-party copyrighted text, images, or rules. You are strictly prohibited from submitting such content to the public repository.

## 3. Trademark and Content Restrictions

To protect the project and comply with intellectual property law, the following restrictions apply to the public version of the project (`neutral` mode):
-   **Forbidden Terms:** The codebase, documentation, and user interface must not use protected trademarks. A list of these terms is maintained in `settings.yaml` and enforced by the CI `term_guard.py` script.
-   **Forbidden Imagery:** The project must not use any logos, symbols (e.g., the Aquila), or other visual assets that are the property of Games Workshop.

## 4. Compliance Procedures & DMCA

This project respects intellectual property rights. If you believe that your copyright has been infringed upon, please submit a DMCA takedown notice to the repository owner with the required information. All valid notices will be processed in accordance with the platform's (e.g., GitHub's) DMCA policy.

## 5. Licensing

-   **Code License:** The source code of the Novel Engine framework is licensed under the [MIT License](LICENSE). This license applies **only** to the original code written for this project.
-   **Content License:**
    -   The original, neutral canon provided in `canon_neutral/` is licensed under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).
    -   This project does not grant you any license to use third-party intellectual property. The responsibility to ensure you have the legal right to use any materials with the `fan` mode rests solely with you, the user.

## 6. `fan` Mode Compliance Conditions

The `fan` mode is a feature intended for users to experiment with the engine **on their local machines using materials they legally own**. To use this mode, the following conditions are enforced by the software at startup:
1.  A `private/registry.yaml` file must exist.
2.  This file must contain a `compliance` section.
3.  The `compliance` section must explicitly state `non_commercial: true` and `distribution: "local_only"`.

If these conditions are not met, the application will refuse to start in `fan` mode. This is a technical safeguard to prevent accidental misuse.
