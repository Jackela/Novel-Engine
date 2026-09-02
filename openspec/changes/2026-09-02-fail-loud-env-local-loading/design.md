# Design: narrow optional environment-file handling

## Read boundary

`mergedEnvironment` reads the optional file through one narrow filesystem
boundary. It catches only to inspect the original error code: `ENOENT` yields
no file values, while every other value is rethrown unchanged. The catch does
not wrap, log, sanitize, or replace the error, so its code, path, cause, and
stack remain available to the CLI's existing failure channel.

The returned text is parsed after that catch boundary. A parser exception is
therefore a programming/configuration failure rather than an absent-file case.
Process variables are merged only after the file is either read and parsed or
confirmed absent, preserving the existing case-insensitive override order.

## Side-effect order

The CLI operational composition root loads configuration before `serve`
builds the API, or another command opens, locks, backs up, imports, or inspects
the database. The loader remains synchronous and side-effect free apart from
reading the selected file, so a non-`ENOENT` failure stops each CLI path at its
earliest owning boundary. `buildApp` continues to accept an already resolved
configuration and does not become a second environment-file owner.
