import type { ComponentProps, PropsWithChildren } from 'react';

import { Button as UIButton } from '@/components/ui/button';

type ButtonVariant = 'primary' | 'secondary' | 'ghost';

interface ButtonProps extends Omit<ComponentProps<typeof UIButton>, 'variant'> {
  variant?: ButtonVariant;
}

const variantMap: Record<ButtonVariant, ComponentProps<typeof UIButton>['variant']> = {
  primary: 'default',
  secondary: 'secondary',
  ghost: 'ghost',
};

export function Button({
  children,
  className,
  variant = 'primary',
  ...props
}: PropsWithChildren<ButtonProps>) {
  return (
    <UIButton className={className} variant={variantMap[variant]} {...props}>
      {children}
    </UIButton>
  );
}
