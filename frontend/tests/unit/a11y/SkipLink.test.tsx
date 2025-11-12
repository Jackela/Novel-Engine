import { render, screen } from '@testing-library/react';
import { axe, toHaveNoViolations } from 'jest-axe';
import userEvent from '@testing-library/user-event';
import { SkipLink } from '../../../src/components/a11y/SkipLink';

expect.extend(toHaveNoViolations);

describe('SkipLink', () => {
  it('should not have accessibility violations', async () => {
    const { container } = render(
      <>
        <SkipLink targetId="main-content" text="Skip to main content" />
        <div id="main-content" tabIndex={-1}>
          Main content
        </div>
      </>
    );
    const results = await axe(container);
    expect(results).toHaveNoViolations();
  });

  it('should render with correct href', () => {
    render(
      <>
        <SkipLink targetId="main-content" text="Skip to main content" />
        <div id="main-content">Main content</div>
      </>
    );
    
    const link = screen.getByText('Skip to main content');
    expect(link).toHaveAttribute('href', '#main-content');
  });

  it('should be visually hidden by default', () => {
    render(
      <>
        <SkipLink targetId="main-content" text="Skip to main content" />
        <div id="main-content">Main content</div>
      </>
    );
    
    const link = screen.getByText('Skip to main content');
    const styles = window.getComputedStyle(link);
    
    expect(styles.position).toBe('absolute');
  });

  it('should become visible on focus', async () => {
    const user = userEvent.setup();
    
    render(
      <>
        <SkipLink targetId="main-content" text="Skip to main content" />
        <div id="main-content">Main content</div>
      </>
    );
    
    const link = screen.getByText('Skip to main content');
    
    await user.tab();
    expect(link).toHaveFocus();
  });

  it('should focus target element when activated', async () => {
    const user = userEvent.setup();
    
    render(
      <>
        <SkipLink targetId="main-content" text="Skip to main content" />
        <div id="main-content" tabIndex={-1}>
          Main content
        </div>
      </>
    );
    
    const link = screen.getByText('Skip to main content');
    const target = screen.getByText('Main content');
    
    await user.click(link);
    
    expect(target).toHaveFocus();
  });

  it('should work with keyboard Enter key', async () => {
    const user = userEvent.setup();
    
    render(
      <>
        <SkipLink targetId="main-content" text="Skip to main content" />
        <div id="main-content" tabIndex={-1}>
          Main content
        </div>
      </>
    );
    
    const link = screen.getByText('Skip to main content');
    const target = screen.getByText('Main content');
    
    link.focus();
    await user.keyboard('{Enter}');
    
    expect(target).toHaveFocus();
  });

  it('should support custom className', () => {
    render(
      <>
        <SkipLink 
          targetId="main-content" 
          text="Skip to main content"
          className="custom-skip-link"
        />
        <div id="main-content">Main content</div>
      </>
    );
    
    const link = screen.getByText('Skip to main content');
    expect(link).toHaveClass('custom-skip-link');
  });

  it('should log warning if target element does not exist', () => {
    const consoleWarnSpy = vi.spyOn(console, 'warn').mockImplementation(() => {});
    
    render(
      <SkipLink targetId="non-existent" text="Skip to content" />
    );
    
    const link = screen.getByText('Skip to content');
    link.click();
    
    expect(consoleWarnSpy).toHaveBeenCalledWith(
      expect.stringContaining('Target element with id "non-existent" not found')
    );
    
    consoleWarnSpy.mockRestore();
  });
});
