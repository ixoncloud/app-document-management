export function formatBytesValue(value: number, locale: string, decimals = 2) {
  const chars = ['', 'k', 'M', 'G', 'T', 'P'];
  let i = 0;
  while (value >= 950 && i < chars.length - 1) {
    value /= 1000;
    i++;
  }

  const formatter = new Intl.NumberFormat(locale, {
    maximumFractionDigits: decimals,
  });
  return `${formatter.format(value)} ${chars[i]}B`;
}
