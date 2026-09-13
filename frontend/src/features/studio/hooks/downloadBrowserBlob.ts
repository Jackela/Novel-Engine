interface BrowserBlobDownload {
  readonly activeObjectUrls: Set<string>;
  readonly blob: Blob;
  readonly filename: string;
  readonly shouldDownload: () => boolean;
}

/** Click a browser download and keep every created object URL on a bounded lifecycle. */
export async function downloadBrowserBlob({
  activeObjectUrls,
  blob,
  filename,
  shouldDownload,
}: BrowserBlobDownload): Promise<void> {
  const objectUrl = URL.createObjectURL(blob);
  activeObjectUrls.add(objectUrl);
  let failure: { readonly reason: unknown } | null = null;
  let link: HTMLAnchorElement | null = null;
  try {
    if (shouldDownload()) {
      link = document.createElement("a");
      link.href = objectUrl;
      link.download = filename;
      document.body.appendChild(link);
      link.click();
    }
  } catch (reason) {
    failure = { reason };
  }
  try {
    link?.remove();
  } catch (reason) {
    failure ??= { reason };
  }
  setTimeout(() => {
    activeObjectUrls.delete(objectUrl);
    URL.revokeObjectURL(objectUrl);
  }, 100);
  if (failure) throw failure.reason;
}
