import { render, screen } from '@testing-library/react';
import { axe, toHaveNoViolations } from 'jest-axe';
import userEvent from '@testing-library/user-event';
import { FocusTrap } from '../../../src/components/a11y/FocusTrap';

expect.extend(toHaveNoViolations);

describe('FocusTrap', () => {
  it('should not have accessibility violations', async () => {
    const { container } = render(
      <FocusTrap>
        <div>
          <button>First button</button>
          <button>Second button</button>
        </div>
      </FocusTrap>
    );
    const results = await axe(container);
    expect(results).toHaveNoViolations();
  });

  it('should focus first focusable element on mount', () => {
    render(
      <FocusTrap>
        <div>
          <button>First button</button>
          <button>Second button</button>
        </div>
      </FocusTrap>
    );
    
    const firstButton = screen.getByText('First button');
    expect(firstButton).toHaveFocus();
  });

  it('should trap focus within container using Tab', async () => {
    const user = userEvent.setup();
    
    render(
      <FocusTrap>
        <div>
          <button>First button</button>
          <button>Second button</button>
        </div>
      </FocusTrap>
    );
    
    const firstButton = screen.getByText('First button');
    const secondButton = screen.getByText('Second button');
    
    expect(firstButton).toHaveFocus();
    
    await user.tab();
    expect(secondButton).toHaveFocus();
    
    await user.tab();
    expect(firstButton).toHaveFocus();
  });

  it('should trap focus backward using Shift+Tab', async () => {
    const user = userEvent.setup();
    
    render(
      <FocusTrap>
        <div>
          <button>First button</button>
          <button>Second button</button>
        </div>
      </FocusTrap>
    );
    
    const firstButton = screen.getByText('First button');
    const secondButton = screen.getByText('Second button');
    
    expect(firstButton).toHaveFocus();
    
    await user.tab({ shift: true });
    expect(secondButton).toHaveFocus();
    
    await user.tab({ shift: true });
    expect(firstButton).toHaveFocus();
  });

  it('should call onClose when Escape key is pressed', async () => {
    const user = userEvent.setup();
    const handleClose = vi.fn();
    
    render(
      <FocusTrap onClose={handleClose}>
        <div>
          <button>First button</button>
        </div>
      </FocusTrap>
    );
    
    await user.keyboard('{Escape}');
    
    expect(handleClose).toHaveBeenCalledTimes(1);
  });

  it('should restore focus to previous element on unmount', () => {
    const outsideButton = document.createElement('button');
    outsideButton.textContent = 'Outside button';
    document.body.appendChild(outsideButton);
    outsideButton.focus();
    
    const { unmount } = render(
      <FocusTrap>
        <div>
          <button>Inside button</button>
        </div>
      </FocusTrap>
    );
    
    const insideButton = screen.getByText('Inside button');
    expect(insideButton).toHaveFocus();
    
    unmount();
    
    expect(outsideButton).toHaveFocus();
    
    document.body.removeChild(outsideButton);
  });

  it('should ignore disabled elements when trapping focus', async () => {
    const user = userEvent.setup();
    
    render(
      <FocusTrap>
        <div>
          <button>First button</button>
          <button disabled>Disabled button</button>
          <button>Third button</button>
        </div>
      </FocusTrap>
    );
    
    const firstButton = screen.getByText('First button');
    const thirdButton = screen.getByText('Third button');
    
    expect(firstButton).toHaveFocus();
    
    await user.tab();
    expect(thirdButton).toHaveFocus();
    
    await user.tab();
    expect(firstButton).toHaveFocus();
  });

  it('should include links and inputs in focus trap', async () => {
    const user = userEvent.setup();
    
    render(
      <FocusTrap>
        <div>
          <button>Button</button>
          <a href="#">Link</a>
          <input type="text" placeholder="Input" />
        </div>
      </FocusTrap>
    );
    
    const button = screen.getByText('Button');
    const link = screen.getByText('Link');
    const input = screen.getByPlaceholderText('Input');
    
    expect(button).toHaveFocus();
    
    await user.tab();
    expect(link).toHaveFocus();
    
    await user.tab();
    expect(input).toHaveFocus();
    
    await user.tab();
    expect(button).toHaveFocus();
  });
});
