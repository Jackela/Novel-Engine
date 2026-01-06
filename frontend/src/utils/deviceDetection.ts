export const isMobileDevice = (): boolean => {
  if (typeof window === 'undefined') return false;

  const userAgent = navigator.userAgent || '';
  const isMobileUA = /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(userAgent);
  const hasTouch = navigator.maxTouchPoints > 0;
  const coarsePointer = typeof window.matchMedia === 'function'
    ? window.matchMedia('(pointer: coarse)').matches
    : false;
  const smallViewport = window.innerWidth <= 768;

  return isMobileUA || (hasTouch && (coarsePointer || smallViewport));
};
