import type { ObjectStorageObjectMeta } from '@ixon-cdk/types';

export type FileListEntry = {
  meta: ObjectStorageObjectMeta;
  name: string;
  size: string;
};

export type FileList = Array<FileListEntry>;
