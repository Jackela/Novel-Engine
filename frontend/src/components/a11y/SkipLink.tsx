import React from 'react';

type MouseEvent = React.MouseEvent<HTMLAnchorElement>;
type KeyboardEvent = React.KeyboardEvent<HTMLAnchorElement>;

interface SkipLinkProps {
  targetId: string;
  text: string;
  className?: string;
}

export const SkipLink: React.FC<SkipLinkProps> = ({
  targetId,
  text,
  className = '',
}) => {
  const handleClick = (event: MouseEvent) => {
    event.preventDefault();
    
    const targetElement = document.getElementById(targetId);
    
    if (targetElement) {
      targetElement.setAttribute('tabIndex', '-1');
      targetElement.focus();
      
      targetElement.addEventListener(
        'blur',
        () => {
          targetElement.removeAttribute('tabIndex');
        },
        { once: true }
      );
    } else {
      console.warn(`Target element with id "${targetId}" not found`);
    }
  };

  const handleKeyDown = (event: KeyboardEvent) => {
    if (event.key === 'Enter') {
      event.preventDefault();
      handleClick(event as any);
    }
  };

  return (
    <a
      href={`#${targetId}`}
      className={`skip-link ${className}`}
      onClick={handleClick}
      onKeyDown={handleKeyDown}
      style={{
        position: 'absolute',
        left: '-9999px',
        width: '1px',
        height: '1px',
        overflow: 'hidden',
      }}
      onFocus={(e) => {
        e.currentTarget.style.position = 'fixed';
        e.currentTarget.style.top = '0';
        e.currentTarget.style.left = '0';
        e.currentTarget.style.width = 'auto';
        e.currentTarget.style.height = 'auto';
        e.currentTarget.style.padding = '0.5rem 1rem';
        e.currentTarget.style.backgroundColor = '#000';
        e.currentTarget.style.color = '#fff';
        e.currentTarget.style.zIndex = '9999';
        e.currentTarget.style.overflow = 'visible';
      }}
      onBlur={(e) => {
        e.currentTarget.style.position = 'absolute';
        e.currentTarget.style.left = '-9999px';
        e.currentTarget.style.width = '1px';
        e.currentTarget.style.height = '1px';
        e.currentTarget.style.overflow = 'hidden';
        e.currentTarget.style.padding = '';
        e.currentTarget.style.backgroundColor = '';
        e.currentTarget.style.color = '';
        e.currentTarget.style.zIndex = '';
      }}
    >
      {text}
    </a>
  );
};
