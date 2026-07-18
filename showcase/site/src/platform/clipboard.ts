export type ClipboardWriter = {
  writeText(text: string): Promise<void>;
};

export type ClipboardCopyResult = "ok" | "unavailable" | "error";

export async function copyText(
  text: string,
  clipboard: ClipboardWriter | undefined = globalThis.navigator?.clipboard,
): Promise<ClipboardCopyResult> {
  if (!clipboard) return "unavailable";

  try {
    await clipboard.writeText(text);
    return "ok";
  } catch {
    return "error";
  }
}
