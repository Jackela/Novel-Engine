import React from 'react';

type MouseEvent = React.MouseEvent<HTMLAnchorElement>;
type KeyboardEvent = React.KeyboardEvent<HTMLAnchorElement>;

interface SkipLinkProps {
  targetId: string;
  text: string;
  className?: string;
  style?: React.CSSProperties;
}

const hiddenBaseStyle: React.CSSProperties = {
  position: 'absolute',
};

export const SkipLink: React.FC<SkipLinkProps> = ({
  targetId,
  text,
  className = '',
  style,
}) => {
  const focusTarget = () => {
    const targetElement = document.getElementById(targetId);

    if (!targetElement) {
      console.warn(`Target element with id "${targetId}" not found`);
      return;
    }

    targetElement.setAttribute('tabIndex', '-1');
    targetElement.focus();

    targetElement.addEventListener(
      'blur',
      () => targetElement.removeAttribute('tabIndex'),
      { once: true }
    );
  };

  const handleClick = (event: MouseEvent) => {
    event.preventDefault();
    focusTarget();
  };

  const handleKeyDown = (event: KeyboardEvent) => {
    if (event.key === 'Enter' || event.key === ' ') {
      event.preventDefault();
      focusTarget();
    }
  };

  return (
    <a
      href={`#${targetId}`}
      className={`skip-link ${className}`}
      onClick={handleClick}
      onKeyDown={handleKeyDown}
      style={{ ...hiddenBaseStyle, ...style }}
    >
      {text}
    </a>
  );
};
