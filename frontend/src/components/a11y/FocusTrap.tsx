import React, { useEffect, useRef } from 'react';
import { useFocusTrap } from '../../hooks/useFocusTrap';

interface FocusTrapProps {
  children: React.ReactNode;
  onClose?: () => void;
  active?: boolean;
  className?: string;
}

export const FocusTrap: React.FC<FocusTrapProps> = ({
  children,
  onClose,
  active = true,
  className = '',
}) => {
  const containerRef = useRef<HTMLDivElement>(null);
  useFocusTrap(containerRef, { enabled: active });

  useEffect(() => {
    if (!active) return;

    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape' && onClose) {
        event.preventDefault();
        onClose();
      }
    };

    document.addEventListener('keydown', handleKeyDown);

    return () => {
      document.removeEventListener('keydown', handleKeyDown);
    };
  }, [active, onClose]);

  return (
    <div ref={containerRef} className={className}>
      {children}
    </div>
  );
};
