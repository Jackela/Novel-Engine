import { render, screen } from '@testing-library/react';
import { axe, toHaveNoViolations } from 'jest-axe';
import userEvent from '@testing-library/user-event';
import { act } from 'react';
import { KeyboardButton } from '../../../src/components/a11y/KeyboardButton';

expect.extend(toHaveNoViolations);

describe('KeyboardButton', () => {
  it('should not have accessibility violations', async () => {
    const { container } = render(
      <KeyboardButton onClick={() => {}}>
        Click me
      </KeyboardButton>
    );
    let results: Awaited<ReturnType<typeof axe>>;
    await act(async () => {
      results = await axe(container);
    });
    expect(results).toHaveNoViolations();
  });

  it('should have role="button"', () => {
    render(
      <KeyboardButton onClick={() => {}}>
        Click me
      </KeyboardButton>
    );
    const button = screen.getByRole('button');
    expect(button).toBeInTheDocument();
  });

  it('should have tabIndex=0 for keyboard focus', () => {
    render(
      <KeyboardButton onClick={() => {}}>
        Click me
      </KeyboardButton>
    );
    const button = screen.getByRole('button');
    expect(button).toHaveAttribute('tabIndex', '0');
  });

  it('should trigger onClick when Enter key is pressed', async () => {
    const user = userEvent.setup();
    const handleClick = vi.fn();
    
    render(
      <KeyboardButton onClick={handleClick}>
        Click me
      </KeyboardButton>
    );
    
    const button = screen.getByRole('button');
    button.focus();
    await user.keyboard('{Enter}');
    
    expect(handleClick).toHaveBeenCalledTimes(1);
  });

  it('should trigger onClick when Space key is pressed', async () => {
    const user = userEvent.setup();
    const handleClick = vi.fn();
    
    render(
      <KeyboardButton onClick={handleClick}>
        Click me
      </KeyboardButton>
    );
    
    const button = screen.getByRole('button');
    button.focus();
    await user.keyboard(' ');
    
    expect(handleClick).toHaveBeenCalledTimes(1);
  });

  it('should support aria-label', () => {
    render(
      <KeyboardButton onClick={() => {}} ariaLabel="Custom label">
        Click me
      </KeyboardButton>
    );
    const button = screen.getByRole('button');
    expect(button).toHaveAttribute('aria-label', 'Custom label');
  });

  it('should support aria-pressed for toggle buttons', () => {
    render(
      <KeyboardButton onClick={() => {}} ariaPressed={true}>
        Toggle me
      </KeyboardButton>
    );
    const button = screen.getByRole('button');
    expect(button).toHaveAttribute('aria-pressed', 'true');
  });

  it('should allow custom className', () => {
    render(
      <KeyboardButton onClick={() => {}} className="custom-class">
        Click me
      </KeyboardButton>
    );
    const button = screen.getByRole('button');
    expect(button).toHaveClass('custom-class');
  });

  it('should forward ref correctly', () => {
    const ref = { current: null };
    render(
      <KeyboardButton onClick={() => {}} ref={ref}>
        Click me
      </KeyboardButton>
    );
    expect(ref.current).toBeInstanceOf(HTMLElement);
  });
});
