/**
 * Ensures `filename` is unique among `files`. If `filename` already exists in
 * the `files` list, will append "` (n)`" before the file's extension. It will
 * seek the first `n` for which the constructed filename does not already exist
 * in `files`.
 *
 * @param filename the new filename that is to be added
 * @param files the already existing filenames
 * @return a new, unique filename (among `files`) based on `filename`
 */
export function createUniqueFilename(filename: string, files: string[] = []): string {
  if (!files.includes(filename)) {
    return filename;
  }

  const extensionStartIndex = filename.lastIndexOf('.');
  const extension = extensionStartIndex > 0 ? filename.slice(extensionStartIndex) : '';
  let name = extensionStartIndex > 0 ? filename.slice(0, extensionStartIndex) : filename;

  const fileNumberPattern = / \((?<number>\d+)\)$/;
  const fileNumberMatchResult = fileNumberPattern.exec(name);
  if (fileNumberMatchResult) {
    const fileNumberIndex = fileNumberMatchResult?.index;
    name = name.slice(0, fileNumberIndex);
  }

  let number = fileNumberMatchResult ? parseInt(fileNumberMatchResult.groups?.['number'] || '0') : 0;
  let newFilename = name;
  do {
    ++number;
    newFilename = `${name} (${number})${extension}`;
  } while (files.includes(newFilename));

  return newFilename.trim();
}
