/**
 * Markdown renderer component with syntax highlighting
 *
 * OPT-008: Markdown + Code Highlighting in Chat
 *
 * Why: Improve readability of AI responses by rendering markdown with
 * syntax highlighting for code blocks.
 *
 * Features:
 * - Safe HTML rendering (no raw HTML by default)
 * - Code block highlighting using highlight.js
 * - Styled with Tailwind CSS only (no custom CSS)
 * - Table, list, and heading support
 */

import { useEffect, useRef } from 'react';
import MarkdownIt from 'markdown-it';
import hljs from 'highlight.js';
import { cn } from '@/lib/utils';

// Configure markdown-it with safe settings
const md = new MarkdownIt({
  html: false, // Disable raw HTML for security
  linkify: true, // Auto-convert URLs to links
  typographer: true, // Enable smart quotes and other typography
  highlight: (str: string, lang: string): string => {
    // Use highlight.js for code blocks
    if (lang && hljs.getLanguage(lang)) {
      try {
        const highlighted = hljs.highlight(str, {
          language: lang,
          ignoreIllegals: true,
        }).value;
        // Return with class for styling - no inline styles
        return `<pre class="hljs"><code class="language-${lang}" tabindex="0">${highlighted}</code></pre>`;
      } catch {
        // Fall through to plain text on error
      }
    }
    // For unknown languages or no language specified, render as plain text
    return `<pre class="hljs"><code tabindex="0">${str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')}</code></pre>`;
  },
});

export interface MarkdownProps {
  /** Markdown content to render */
  content: string;
  /** Additional class names for the container */
  className?: string;
}

/**
 * Markdown component with syntax highlighting
 * Renders assistant messages with markdown formatting
 */
export function Markdown({ content, className }: MarkdownProps) {
  const containerRef = useRef<HTMLDivElement>(null);

  // Render markdown to HTML
  const renderedHtml = md.render(content);

  /**
   * Post-process rendered HTML to add accessibility and styling
   * Runs after each render to ensure dynamically added content is processed
   */
  useEffect(() => {
    if (!containerRef.current) return;

    // Add table container for proper scrolling
    const tables = containerRef.current.querySelectorAll('table');
    tables.forEach((table) => {
      const wrapper = document.createElement('div');
      wrapper.className = 'overflow-x-auto my-2';
      table.parentNode?.insertBefore(wrapper, table);
      wrapper.appendChild(table);
    });

    // Make code blocks focusable for keyboard navigation
    const codeBlocks = containerRef.current.querySelectorAll('pre code');
    codeBlocks.forEach((block) => {
      block.setAttribute('tabindex', '0');
    });
  }, [renderedHtml]);

  return (
    <div
      ref={containerRef}
      className={cn(
        'markdown prose prose-sm max-w-none',
        // Tailwind typography for markdown elements
        '[&_h1]:mb-2 [&_h1]:text-lg [&_h1]:font-semibold',
        '[&_h2]:mb-2 [&_h2]:text-base [&_h2]:font-semibold',
        '[&_h3]:mb-1 [&_h3]:text-sm [&_h3]:font-medium',
        '[&_p]:my-1 [&_p]:text-sm',
        '[&_ul]:my-1 [&_ul]:list-disc [&_ul]:pl-4',
        '[&_ol]:my-1 [&_ol]:list-decimal [&_ol]:pl-4',
        '[&_li]:my-0.5',
        '[&_a]:text-primary [&_a]:underline [&_a]:underline-offset-2',
        '[&_blockquote]:border-l-2 [&_blockquote]:border-muted-foreground [&_blockquote]:pl-3 [&_blockquote]:italic',
        // Table styling with Tailwind
        '[&_table]:my-2 [&_table]:w-full [&_table]:border-collapse',
        '[&_th]:border [&_th]:border-border [&_th]:bg-muted [&_th]:px-2 [&_th]:py-1 [&_th]:text-left [&_th]:text-xs [&_th]:font-medium',
        '[&_td]:border [&_td]:border-border [&_td]:px-2 [&_td]:py-1 [&_td]:text-sm',
        // Code block styling
        '[&_pre]:my-2 [&_pre]:overflow-x-auto [&_pre]:rounded-md [&_pre]:bg-muted [&_pre]:p-3',
        '[&_code]:font-mono [&_code]:text-sm',
        '[&_pre_code]:bg-transparent [&_pre_code]:p-0',
        // Inline code styling (inside p, li, etc. but not inside pre)
        '[&&:not(pre)>code]:bg-muted [&&:not(pre)>code]:px-1 [&&:not(pre)>code]:py-0.5 [&:not(pre)>code]:rounded',
        // Horizontal rule
        '[&_hr]:my-2 [&_hr]:border-border',
        className
      )}
      dangerouslySetInnerHTML={{ __html: renderedHtml }}
    />
  );
}

/**
 * Plain text message component for user messages
 * User messages remain plain text without markdown rendering
 */
export function PlainText({
  content,
  className,
}: {
  content: string;
  className?: string;
}) {
  return (
    <p className={cn('whitespace-pre-wrap break-words text-sm', className)}>
      {content}
    </p>
  );
}

export default Markdown;
