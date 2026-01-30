/**
 * NarrativePage - Story narrative management
 * Full-page view for narrative generation and editing
 */
import { Suspense } from 'react';
import { BookOpen, Sparkles, FileText, History, Wand2 } from 'lucide-react';
import {
  Card,
  CardHeader,
  CardTitle,
  CardContent,
  CardDescription,
} from '@/shared/components/ui/Card';
import { Button } from '@/shared/components/ui';
import { LoadingSpinner } from '@/shared/components/feedback';

function NarrativeEditor() {
  return (
    <Card className="h-full" data-testid="narrative-editor">
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="flex items-center gap-2">
              <BookOpen className="h-5 w-5 text-primary" />
              Narrative Editor
            </CardTitle>
            <CardDescription>Write and generate your story</CardDescription>
          </div>
          <div className="flex gap-2">
            <Button variant="outline" size="sm">
              <History className="mr-2 h-4 w-4" />
              History
            </Button>
            <Button size="sm">
              <Wand2 className="mr-2 h-4 w-4" />
              Generate
            </Button>
          </div>
        </div>
      </CardHeader>
      <CardContent>
        <div className="min-h-[400px] rounded-lg border bg-background p-4">
          <div className="prose prose-sm dark:prose-invert max-w-none">
            <p className="leading-relaxed">
              The morning mist clung to the cobblestone streets as Aldric made his way
              through the quiet marketplace. Merchants were just beginning to set up
              their stalls, their hushed voices carrying in the cool air.
            </p>
            <p className="mt-4 leading-relaxed">
              He paused at the fountain in the center square, eyes scanning the crowd
              for any sign of his contact. The message had been clear: dawn at the
              market, come alone.
            </p>
            <p className="mt-4 leading-relaxed text-muted-foreground/60">
              <Sparkles className="mr-1 inline h-4 w-4 animate-pulse text-primary" />
              <span className="italic">Continue the story...</span>
            </p>
          </div>
        </div>
        <div className="mt-4 flex items-center justify-between text-xs text-muted-foreground">
          <span>Last saved: 2 min ago</span>
          <span>1,247 words</span>
        </div>
      </CardContent>
    </Card>
  );
}

function ChaptersList() {
  const chapters = [
    { title: 'Chapter 1: The Beginning', words: 2500, status: 'complete' },
    { title: 'Chapter 2: The Journey', words: 3200, status: 'complete' },
    { title: 'Chapter 3: The Encounter', words: 1247, status: 'in_progress' },
    { title: 'Chapter 4: The Revelation', words: 0, status: 'draft' },
  ];

  const getStatusStyle = (status: string) => {
    switch (status) {
      case 'complete':
        return 'bg-green-500/10 text-green-600';
      case 'in_progress':
        return 'bg-yellow-500/10 text-yellow-600';
      default:
        return 'bg-muted text-muted-foreground';
    }
  };

  return (
    <Card data-testid="chapters-list">
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <FileText className="h-5 w-5 text-primary" />
          Chapters
        </CardTitle>
        <CardDescription>Your story structure</CardDescription>
      </CardHeader>
      <CardContent>
        <div className="space-y-2">
          {chapters.map((chapter, index) => (
            <div
              key={index}
              className="flex cursor-pointer items-center justify-between rounded-lg p-3 transition-colors hover:bg-muted/50"
            >
              <div>
                <p className="text-sm font-medium">{chapter.title}</p>
                <p className="text-xs text-muted-foreground">
                  {chapter.words.toLocaleString()} words
                </p>
              </div>
              <span
                className={`rounded-full px-2 py-1 text-xs capitalize ${getStatusStyle(chapter.status)}`}
              >
                {chapter.status.replace('_', ' ')}
              </span>
            </div>
          ))}
        </div>
        <Button variant="outline" className="mt-4 w-full">
          Add Chapter
        </Button>
      </CardContent>
    </Card>
  );
}

function GenerationStats() {
  return (
    <Card data-testid="generation-stats">
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Sparkles className="h-5 w-5 text-primary" />
          Generation Stats
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          <div>
            <div className="flex justify-between text-sm">
              <span>Daily Tokens</span>
              <span>8,500 / 10,000</span>
            </div>
            <div className="mt-1 h-2 rounded-full bg-muted">
              <div className="h-full w-[85%] rounded-full bg-primary" />
            </div>
          </div>
          <div className="grid grid-cols-2 gap-4 pt-2">
            <div className="text-center">
              <p className="text-2xl font-bold">24</p>
              <p className="text-xs text-muted-foreground">Generations Today</p>
            </div>
            <div className="text-center">
              <p className="text-2xl font-bold">6,947</p>
              <p className="text-xs text-muted-foreground">Total Words</p>
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

export default function NarrativePage() {
  return (
    <Suspense fallback={<LoadingSpinner fullScreen text="Loading narrative..." />}>
      <div className="space-y-6" data-testid="narrative-page">
        {/* Page header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold tracking-tight">Narrative Studio</h1>
            <p className="text-muted-foreground">
              Create and manage your story narrative
            </p>
          </div>
        </div>

        {/* Main content grid */}
        <div className="grid gap-6 lg:grid-cols-3">
          {/* Editor takes 2 columns */}
          <div className="lg:col-span-2">
            <NarrativeEditor />
          </div>

          {/* Sidebar */}
          <div className="space-y-6">
            <ChaptersList />
            <GenerationStats />
          </div>
        </div>
      </div>
    </Suspense>
  );
}
