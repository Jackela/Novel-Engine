/** `entry.*` screen messages (sign-in / owner creation). Merged into `en.ts`. */
export const enEntry = {
  "entry.heading.signedIn": "Open your writing studio",
  "entry.heading.createOwner": "Create the local owner",
  "entry.heading.unavailable": "Unable to open your writing studio",
  "entry.heading.loading": "Opening your writing studio",
  "entry.intro.selfHosted":
    "Your projects, Markdown revisions, reviews, and exports stay in this self-hosted instance.",
  "entry.intro.trialProvider":
    "No API key? Generation runs on the built-in trial provider — connect a real one in a project's Settings when you're ready.",
  "entry.notice.sessionExpired": "Your session expired. Sign in again to return to where you were.",
  "entry.field.username": "Username",
  "entry.field.password": "Password",
  "entry.field.confirmPassword": "Confirm password",
  "entry.field.setupToken": "First-start setup token",
  "entry.hint.setupToken":
    "Optional — only a first start behind Docker or another non-loopback address needs it: " +
    "paste the one-time token from the server log (or the .setup-token file in the data " +
    "directory). Loopback setup leaves it empty.",
  "entry.hint.noRecovery":
    "There is no email recovery by design. Save this password: if it is lost, stop the server " +
    "and run novel-engine owner reset to create a new owner. Book content is never touched.",
  "entry.action.signIn": "Sign in",
  "entry.action.signingIn": "Signing in...",
  "entry.action.createOwner": "Create owner",
  "entry.action.creatingOwner": "Creating owner...",
  "entry.status.checkingSession": "Checking your session...",
  "entry.error.unableToContinue": "Unable to continue.",
  "entry.error.unableToCheckOwner": "Unable to check the local owner.",
  "entry.error.passwordMismatch": "Passwords do not match.",
  "entry.error.invalidCredentials": "Incorrect username or password.",
  "entry.error.setupTokenInvalid":
    "This first start needs the one-time setup token for a non-loopback address: read it from " +
    "the server log (or the .setup-token file in the data directory) and paste it into the " +
    "field above. Loopback setup needs no token.",
} as const;
