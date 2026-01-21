/**
 * LoginPage - Authentication page for the application
 */
import { useState } from 'react';
import { useNavigate } from '@tanstack/react-router';
import { Lock, Eye, EyeOff, ArrowLeft, AlertCircle, Info } from 'lucide-react';
import { Button, Card, CardContent, Input, Label } from '@/shared/components/ui';
import { useAuth } from '@/features/auth';
import config from '../config/env';

interface LoginFormFieldsProps {
  email: string;
  password: string;
  showPassword: boolean;
  rememberMe: boolean;
  emailError: boolean;
  passwordError: boolean;
  error: Error | null;
  onEmailChange: (value: string) => void;
  onPasswordChange: (value: string) => void;
  onEmailBlur: () => void;
  onPasswordBlur: () => void;
  onTogglePassword: () => void;
  onRememberMeChange: (value: boolean) => void;
}

function LoginFormFields({
  email,
  password,
  showPassword,
  rememberMe,
  emailError,
  passwordError,
  error,
  onEmailChange,
  onPasswordChange,
  onEmailBlur,
  onPasswordBlur,
  onTogglePassword,
  onRememberMeChange,
}: LoginFormFieldsProps) {
  return (
    <>
      {error && (
        <div className="flex items-center gap-2 p-3 rounded-lg bg-destructive/10 text-destructive">
          <AlertCircle className="h-4 w-4 flex-shrink-0" />
          <span className="text-sm">{error.message || 'Authentication failed'}</span>
        </div>
      )}

      <div className="space-y-2">
        <Label htmlFor="email">Email</Label>
        <Input
          id="email"
          type="email"
          placeholder="Enter your email"
          value={email}
          onChange={(e) => onEmailChange(e.target.value)}
          onBlur={onEmailBlur}
          className={emailError ? 'border-destructive' : ''}
          required
        />
        {emailError && <p className="text-xs text-destructive">Email is required.</p>}
      </div>

      <div className="space-y-2">
        <Label htmlFor="password">Password</Label>
        <div className="relative">
          <Input
            id="password"
            type={showPassword ? 'text' : 'password'}
            placeholder="Enter your password"
            value={password}
            onChange={(e) => onPasswordChange(e.target.value)}
            onBlur={onPasswordBlur}
            className={`pr-10 ${passwordError ? 'border-destructive' : ''}`}
            required
          />
          <button
            type="button"
            onClick={onTogglePassword}
            className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground transition-colors"
            aria-label={showPassword ? 'Hide password' : 'Show password'}
          >
            {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
          </button>
        </div>
        {passwordError && <p className="text-xs text-destructive">Password is required.</p>}
      </div>

      <div className="flex items-center gap-2">
        <input
          type="checkbox"
          id="rememberMe"
          checked={rememberMe}
          onChange={(e) => onRememberMeChange(e.target.checked)}
          className="h-4 w-4 rounded border-input accent-primary"
        />
        <Label htmlFor="rememberMe" className="text-sm font-normal cursor-pointer">
          Remember this device
        </Label>
      </div>
    </>
  );
}

interface LoginFormActionsProps {
  isLoading: boolean;
  demoMode: boolean;
  onGuest: () => void;
}

function LoginFormActions({ isLoading, demoMode, onGuest }: LoginFormActionsProps) {
  return (
    <div className="space-y-3">
      <Button type="submit" size="lg" className="w-full" disabled={isLoading}>
        {isLoading ? 'Authenticating...' : 'Sign in'}
      </Button>

      {demoMode && (
        <Button type="button" variant="outline" size="lg" className="w-full" onClick={onGuest}>
          Continue as guest
        </Button>
      )}
    </div>
  );
}

interface LoginSupportPanelProps {
  demoMode: boolean;
}

function LoginSupportPanel({ demoMode }: LoginSupportPanelProps) {
  return (
    <div className="space-y-2">
      <p className="text-xs uppercase tracking-widest text-muted-foreground">Support</p>
      {demoMode ? (
        <div className="flex items-start gap-2 p-3 rounded-lg border bg-muted/50">
          <Info className="h-4 w-4 text-primary mt-0.5 flex-shrink-0" />
          <span className="text-sm text-muted-foreground">
            Demo mode is enabled. Guest sessions are available and do not require credentials.
          </span>
        </div>
      ) : (
        <p className="text-sm text-muted-foreground">
          Need access? Email{' '}
          <a href="mailto:ops@novel.engine" className="text-primary hover:underline">
            ops@novel.engine
          </a>{' '}
          or request credentials in the operator handbook.
        </p>
      )}
    </div>
  );
}

function LoginIntroPanel() {
  return (
    <Card className="h-full">
      <CardContent className="p-6 md:p-8 h-full flex flex-col justify-between">
        <div className="space-y-6">
          <div className="w-13 h-13 rounded-full bg-primary/10 flex items-center justify-center">
            <Lock className="h-7 w-7 text-primary" />
          </div>
          <div className="space-y-2">
            <h1 className="text-3xl md:text-4xl font-semibold tracking-tight">Access console</h1>
            <p className="text-muted-foreground">
              Sign in to resume your operational workspace and manage live narratives.
            </p>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

interface LoginFormPanelProps {
  email: string;
  password: string;
  showPassword: boolean;
  rememberMe: boolean;
  emailError: boolean;
  passwordError: boolean;
  error: Error | null;
  isLoading: boolean;
  demoMode: boolean;
  onEmailChange: (value: string) => void;
  onPasswordChange: (value: string) => void;
  onEmailBlur: () => void;
  onPasswordBlur: () => void;
  onTogglePassword: () => void;
  onRememberMeChange: (value: boolean) => void;
  onSubmit: (event: React.FormEvent) => void;
  onGuest: () => void;
  onReturn: () => void;
}

function LoginFormPanel({
  email,
  password,
  showPassword,
  rememberMe,
  emailError,
  passwordError,
  error,
  isLoading,
  demoMode,
  onEmailChange,
  onPasswordChange,
  onEmailBlur,
  onPasswordBlur,
  onTogglePassword,
  onRememberMeChange,
  onSubmit,
  onGuest,
  onReturn,
}: LoginFormPanelProps) {
  return (
    <Card className="h-full">
      <CardContent className="p-6 md:p-8 space-y-6">
        <div className="space-y-1">
          <p className="text-xs uppercase tracking-widest text-muted-foreground">Operator login</p>
          <h2 className="text-xl font-semibold">Welcome back</h2>
        </div>

        <form onSubmit={onSubmit} className="space-y-4">
          <LoginFormFields
            email={email}
            password={password}
            showPassword={showPassword}
            rememberMe={rememberMe}
            emailError={emailError}
            passwordError={passwordError}
            error={error}
            onEmailChange={onEmailChange}
            onPasswordChange={onPasswordChange}
            onEmailBlur={onEmailBlur}
            onPasswordBlur={onPasswordBlur}
            onTogglePassword={onTogglePassword}
            onRememberMeChange={onRememberMeChange}
          />
          <LoginFormActions isLoading={isLoading} demoMode={demoMode} onGuest={onGuest} />
        </form>

        <LoginSupportPanel demoMode={demoMode} />

        <div className="h-px bg-border" />

        <Button variant="ghost" onClick={onReturn} className="w-full text-muted-foreground">
          <ArrowLeft className="h-4 w-4 mr-2" />
          Return to overview
        </Button>
      </CardContent>
    </Card>
  );
}

export default function LoginPage() {
  const navigate = useNavigate();
  const { login, loginAsGuest, isLoading, error } = useAuth();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [rememberMe, setRememberMe] = useState(true);
  const [touched, setTouched] = useState({ email: false, password: false });
  const [submitted, setSubmitted] = useState(false);

  const demoMode = config.enableGuestMode;

  const emailError = (touched.email || submitted) && email.trim().length === 0;
  const passwordError = (touched.password || submitted) && password.trim().length === 0;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitted(true);

    if (emailError || passwordError) {
      return;
    }

    try {
      await login({ email, password, remember_me: rememberMe });
      navigate({ to: '/dashboard' });
    } catch {
      // Error handled by auth store
    }
  };

  const handleGuest = async () => {
    await loginAsGuest();
    navigate({ to: '/dashboard' });
  };

  return (
    <main id="main-content" className="min-h-screen flex items-center py-12 md:py-20">
      <div className="container mx-auto px-4 max-w-5xl">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 md:gap-8 items-stretch">
          <LoginIntroPanel />
          <LoginFormPanel
            email={email}
            password={password}
            showPassword={showPassword}
            rememberMe={rememberMe}
            emailError={emailError}
            passwordError={passwordError}
            error={error}
            isLoading={isLoading}
            demoMode={demoMode}
            onEmailChange={setEmail}
            onPasswordChange={setPassword}
            onEmailBlur={() => setTouched((prev) => ({ ...prev, email: true }))}
            onPasswordBlur={() => setTouched((prev) => ({ ...prev, password: true }))}
            onTogglePassword={() => setShowPassword((prev) => !prev)}
            onRememberMeChange={setRememberMe}
            onSubmit={handleSubmit}
            onGuest={handleGuest}
            onReturn={() => navigate({ to: '/' })}
          />
        </div>
      </div>
    </main>
  );
}
