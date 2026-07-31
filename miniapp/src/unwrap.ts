/** `{data, meta}` konvertini ochish.
 *
 * ⚠️ Faqat **sof konvert** ochiladi. Hisobot obyektining o'zida ham `data`
 * maydoni bor (forma qiymatlari) — uni konvert deb o'qish `id` ni yo'qotardi
 * va Mini App `GET /submissions/undefined` so'rovini yuborardi (HTTP 422).
 */
export function unwrap<T>(payload: unknown): T {
  if (payload && typeof payload === 'object' && !Array.isArray(payload)) {
    const keys = Object.keys(payload as Record<string, unknown>);
    const isEnvelope =
      keys.includes('data') && keys.every((key) => key === 'data' || key === 'meta');
    if (isEnvelope) return (payload as { data: T }).data;
  }
  return payload as T;
}
