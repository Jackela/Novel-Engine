import { Loader2 } from 'lucide-react';
import { useNavigate, useParams } from 'react-router-dom';

import { StudioPageView } from './StudioPageView';
import { useStudioPageModel } from './hooks/useStudioPageModel';

export function StudioPage() {
  const { projectId = '', section = 'manuscript' } = useParams();
  const navigate = useNavigate();
  const { project, viewProps } = useStudioPageModel(projectId, section, navigate);

  if (!project || !viewProps) {
    return (
      <main className="studio-loading">
        <Loader2 className="spin" /> Loading Studio
      </main>
    );
  }

  return <StudioPageView {...viewProps} />;
}
