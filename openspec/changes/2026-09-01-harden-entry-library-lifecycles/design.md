# Design: entry and project-library lifecycle ownership

## Bootstrap ownership

Each mounted entry or library surface owns one abort controller and one request
epoch. Cleanup invalidates the epoch before aborting the controller. A request
may publish state or navigate only while both its surface and epoch remain
current. Entry checks the session first; only an authenticated result navigates.
An unauthenticated response may start the setup-status read, but an operational
session failure is displayed directly and does not masquerade as first-run
setup.

The project library checks the session before loading projects. HTTP 401 alone
returns to entry. Project-list network, timeout, parse, and server failures keep
the library route and expose Retry. Retrying supersedes and aborts the previous
read before starting a new one.

## Mutation ownership

Retry, create-project, and logout commands share one synchronous command owner
in addition to rendered disabled state. This prevents same-render duplicate or
conflicting activations in either direction. Mutation transports are not
described as cancellable because cancellation cannot prove that the server did
not commit. Late mutation completion may navigate only while the originating
surface still owns the invocation.

## Accessibility and focus

Loading and mutation initiators expose `aria-busy`; related controls can be
disabled without changing their accessible names. Operational failures use
`role="alert"`. Retry uses the shared focus-restoration rule: return focus to
the initiator only if the author did not move elsewhere while the request was
pending.
