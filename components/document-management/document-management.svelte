<script lang="ts">
  import type {
    ComponentContext,
    ObjectStorageClient,
    ObjectStorageObjectMeta,
    ResourceDataClient,
  } from '@ixon-cdk/types';

  import { formatBytesValue } from './formatters/format-bytes/format-bytes.utils';

  import { naturalSort } from './lib/natural-sort';
  import { onMount } from 'svelte';

  import { createUniqueFilename } from './document-management.utils';
  import type { FileList, FileListEntry } from './types';

  export let context: ComponentContext<{}>;

  let rootEl: HTMLDivElement;
  let translations: { [key: string]: string } = {};
  let width: number | null = null;
  let objectStorageClient: ObjectStorageClient;
  let loaded = true;
  let resourceDataClient: ResourceDataClient;
  let objects: Array<ObjectStorageObjectMeta> = [];
  let uploadAllowed = false;
  let files: FileList = [];

  $: isNarrow = width !== null ? width <= 460 : false;
  $: uploadDisabled = objects.length >= 100;

  $: objectsToFileList(objects);
  function objectsToFileList(_objects: Array<ObjectStorageObjectMeta>) {
    const sortBy = naturalSort();
    files = _objects
      .map(e => {
        return {
          name: e.tags?.name.toString() ?? e.uuid ?? '',
          meta: e,
          size: formatBytesValue(e.size ?? -1, context.appData.locale, 0),
        };
      })
      .sort((a, b) => sortBy(a.name, b.name));
  }

  onMount(async () => {
    objectStorageClient = context.createObjectStorageClient();
    resourceDataClient = context.createResourceDataClient();

    translations = context.translate(
      ['ADD_DOCUMENT', 'DOCUMENTATION', 'NAME', 'NO_DOCUMENTS', 'SIZE'],
      undefined,
      { source: 'global' },
    );

    resourceDataClient.query(
      [
        { selector: 'Agent', fields: ['permissions'] },
        { selector: 'Asset', fields: ['permissions'] },
      ],
      ([agent, asset]) => {
        const agentOrAsset = agent.data ?? asset.data;
        uploadAllowed =
          agentOrAsset?.permissions?.includes('COMPANY_ADMIN') === true ||
          agentOrAsset?.permissions?.includes('MANAGE_AGENT') === true;
      },
    );

    try {
      const list = await objectStorageClient.getList();
      objects = list.entries;
    } catch (e) {
      objects = [];
    }

    width = rootEl.getBoundingClientRect().width;
    const resizeObserver = new ResizeObserver(entries => {
      entries.forEach(entry => {
        width = entry.contentRect.width;
      });
    });
    resizeObserver.observe(rootEl);

    return () => {
      resizeObserver.unobserve(rootEl);
    };
  });

  async function handleAddButtonClick(): Promise<void> {
    const result = await context.openFormDialog({
      title: context.translate('ADD_DOCUMENT', undefined, {
        source: 'global',
      }),
      inputs: [
        {
          key: 'file',
          type: 'File',
          label: context.translate('FILE', undefined, { source: 'global' }),
          required: true,
          size: {
            max: 50_000_000,
          },
        },
      ],
      submitButtonText: context.translate('ADD', undefined, {
        source: 'global',
      }),
    });

    if (result && result.value && result.value.file) {
      const { file } = result.value;
      const filename = createUniqueFilename(
        file.name,
        files.map(f => f.name),
      );

      try {
        const uploadResult = await objectStorageClient.store(file, {
          tags: {
            name: filename,
          },
        });

        objects = [
          ...objects,
          {
            uuid: uploadResult.identifier,
            size: file.size,
            tags: {
              name: filename,
            },
          },
        ];
      } catch (e) {
        // Nothing to do
      }
    }
  }

  async function handleDownload(objectMeta: ObjectStorageObjectMeta) {
    const meta = files.find(f => f.meta === objectMeta);
    if (!meta) {
      return;
    }
    try {
      const file = await objectStorageClient.getBlob(objectMeta);
      context.saveAsFile(file, meta.name);
    } catch (e) {
      // Nothing to do
    }
  }

  async function handleRemoveDocumentButtonClick(
    file: FileListEntry,
  ): Promise<void> {
    const confirmed = await context.openConfirmDialog({
      title: context.translate('REMOVE_DOCUMENT'),
      message: context.translate('__TEXT__.CONFIRM_DOCUMENT_REMOVAL', {
        name: file.name,
      }),
      confirmButtonText: context.translate('REMOVE'),
      confirmCheckbox: true,
      destructive: true,
    });
    if (confirmed) {
      try {
        await objectStorageClient.delete(file.meta);
        objects = objects.filter(f => f !== file.meta);
      } catch (e) {
        // Nothing to do
      }
    }
  }

  async function handleMoreActionsButtonClick(
    file: FileListEntry,
  ): Promise<void> {
    const actions = [{ title: context.translate('REMOVE'), destructive: true }];
    const result = await context.openActionBottomSheet({ actions });
    if (result) {
      switch (result.index) {
        case 0:
          await handleRemoveDocumentButtonClick(file);
          break;
      }
    }
  }
</script>

<div class="card" bind:this={rootEl} class:is-narrow={isNarrow}>
  <div class="card-header">
    <h3 class="card-title" data-testid="document-management-card-title">
      {translations.DOCUMENTATION}
    </h3>
    <div class="card-header-actions">
      {#if isNarrow && uploadAllowed}
        <button
          class="icon-button"
          data-testid="document-management-add-button"
          disabled={uploadDisabled}
          on:click={handleAddButtonClick}
        >
          <svg
            width="16"
            height="20"
            viewBox="0 0 16 20"
            fill="none"
            xmlns="http://www.w3.org/2000/svg"
          >
            <path
              d="M9 9H7V12H4V14H7V17H9V14H12V12H9V9ZM10 0H2C0.9 0 0 0.9 0 2V18C0 19.1 0.89 20 1.99 20H14C15.1 20 16 19.1 16 18V6L10 0ZM14 18H2V2H9V7H14V18Z"
            />
          </svg>
        </button>
      {:else if uploadAllowed}
        <button
          class="button"
          data-testid="document-management-add-button"
          disabled={uploadDisabled}
          on:click={handleAddButtonClick}
        >
          <svg height="24" viewBox="0 -960 960 960" width="24"
            ><path
              d="M450-200v-250H200v-60h250v-250h60v250h250v60H510v250h-60Z"
            /></svg
          >
          <span>{translations.ADD_DOCUMENT}</span>
        </button>
      {/if}
    </div>
  </div>
  <div class="card-content">
    {#if loaded}
      {#if files.length}
        <div class="table-wrapper">
          <table
            class="table"
            class:sticky-column={!isNarrow}
            class:narrow={isNarrow}
          >
            <thead data-testid="document-management-table-head">
              <tr>
                <th class="col">{translations.NAME}</th>
                {#if !isNarrow}
                  <th class="col col-size">{translations.SIZE}</th>
                {/if}
                <th class="col col-actions" />
              </tr>
            </thead>
            <tbody>
              {#each files as file}
                <tr class="row" data-testid="document-management-table-row">
                  {#if !isNarrow}
                    <td class="col">
                      <span
                        class="name"
                        title={file.name}
                        on:click={() => handleDownload(file.meta)}
                        >{file.name}</span
                      >
                    </td>
                  {/if}
                  <td class="col">
                    {#if isNarrow}
                      <div on:click={() => handleDownload(file.meta)}>
                        <div class="name">
                          {file.name}
                        </div>
                        <div class="size">
                          {file.size}
                        </div>
                      </div>
                    {:else}
                      <div class="size">
                        {file.size}
                      </div>
                    {/if}
                  </td>
                  <td class="col">
                    {#if uploadAllowed}
                      {#if isNarrow}
                        <button
                          class="icon-button more"
                          data-testid="document-management-more-button"
                          on:click={() => handleMoreActionsButtonClick(file)}
                        >
                          <svg
                            xmlns="http://www.w3.org/2000/svg"
                            height="24px"
                            viewBox="0 0 24 24"
                            width="24px"
                            ><path d="M0 0h24v24H0V0z" fill="none" /><path
                              d="M12 8c1.1 0 2-.9 2-2s-.9-2-2-2-2 .9-2 2 .9 2 2 2zm0 2c-1.1 0-2 .9-2 2s.9 2 2 2 2-.9 2-2-.9-2-2-2zm0 6c-1.1 0-2 .9-2 2s.9 2 2 2 2-.9 2-2-.9-2-2-2z"
                            /></svg
                          >
                        </button>
                      {:else}
                        <button
                          class="icon-button remove"
                          data-testid="document-management-remove-button"
                          on:click={() => handleRemoveDocumentButtonClick(file)}
                        >
                          <svg height="20px" viewBox="0 0 24 24" width="20px"
                            ><path d="M0 0h24v24H0V0z" fill="none" /><path
                              d="M16 9v10H8V9h8m-1.5-6h-5l-1 1H5v2h14V4h-3.5l-1-1zM18 7H6v12c0 1.1.9 2 2 2h8c1.1 0 2-.9 2-2V7z"
                            /></svg
                          >
                        </button>
                      {/if}
                    {/if}
                  </td>
                </tr>
              {/each}
            </tbody>
          </table>
        </div>
      {:else}
        <div class="empty-state" data-testid="document-management-empty-state">
          <svg width="24" height="24" viewBox="0 0 24 24" fill="currentColor"
            ><g
              ><rect x="4" y="15" width="10" height="2" /><polygon
                points="9.003,9 7.004,7 4,7 4,9"
              /><polygon points="11.001,11 4,11 4,13 13,13" /><polygon
                points="20,11 13.546,11 15.546,13 20,13"
              /><polygon points="11.546,9 20,9 20,7 9.546,7" /></g
            ><path d="M19.743,22.289l1.27-1.27L2.95,2.956l-1.27,1.28" /></svg
          >
          <p>{translations.NO_DOCUMENTS}</p>
        </div>
      {/if}
    {:else}
      <div class="loading-state">
        <div class="spinner">
          <svg
            preserveAspectRatio="xMidYMid meet"
            focusable="false"
            viewBox="0 0 100 100"
          >
            <circle cx="50%" cy="50%" r="45" />
          </svg>
        </div>
      </div>
    {/if}
  </div>
</div>

<style lang="scss">
  @import './styles/button';
  @import './styles/card';
  @import './styles/spinner';

  .card {
    .card-header {
      display: flex;
      flex-direction: row;
      height: 40px;

      .card-title {
        flex: 1 0 auto;
      }
    }

    &:not(.is-narrow) {
      .card-header {
        height: 52px;
      }

      .card-header-actions {
        padding: 8px;

        @media print {
          display: none;
        }
      }
    }
  }

  .card-header .icon-button {
    svg {
      fill: var(--body-color);
    }

    &:disabled svg {
      fill: #00000042;
    }
  }

  .card-header .button {
    display: flex;
    flex-direction: row;
    align-items: center;
    padding-right: 12px;
    padding-left: 8px;
    background-color: var(--accent);
    line-height: 32px;
    font-size: 14px;
    color: var(--accent-color);

    svg {
      margin-right: 4px;
      fill:  var(--accent-color);
    }

    &:disabled {
      background-color: #0000001f;
      color: #00000042;

      svg {
        fill: #00000042;
      }
    }
  }

  .card-content {
    position: relative;
  }

  .table-wrapper {
    position: absolute;
    left: 0;
    right: 0;
    top: 0;
    bottom: 0;
    padding: 0 8px;
    overflow: auto;
    overflow-anchor: none;
  }

  table {
    width: 100%;
    border-collapse: collapse;
    table-layout: fixed;
    color: rgba(0, 0, 0, 0.87);

    .col-size {
      width: 76px;
    }

    .col-actions {
      width: 40px;
    }

    thead {
      th {
        position: sticky;
        white-space: nowrap;
        background: var(--basic);
        top: 0;
        overflow: hidden;
        text-overflow: ellipsis;
        max-width: 7em;
        z-index: 10;
        text-align: left;
      }

      tr {
        font-weight: 600;

        .col {
          padding: 0 6px 12px 0;
        }
      }
    }

    thead tr,
    tbody tr {
      height: 28px;

      .col:last-child {
        padding-right: 0;
      }
    }

    tbody {
      tr {
        &:hover {
          background-color: #f7f7f7;

          button.icon-button.remove svg {
            fill: var(--body-color);
          }
        }

        button.icon-button.remove svg {
          fill: none;
        }

        button.icon-button.more svg {
          fill: var(--body-color);
        }

        .col {
          padding: 6px 6px 6px 0;
          line-height: 16px;
          border-bottom: 1px solid var(--card-border-color);
          vertical-align: middle;
        }
      }

      td {
        overflow: hidden;
        text-overflow: ellipsis;
      }
    }

    &:not(.narrow) .name {
      color: var(--primary);
    }
  }

  .col-container {
    position: relative;
    padding-right: 20px;

    @media (min-width: 640px) {
      padding-right: 0;
    }
  }

  .col {
    .name {
      margin-bottom: 4px;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;

      &:hover {
        cursor: pointer;
      }
    }

    .name,
    .size {
      white-space: nowrap;
    }

    .size {
      min-width: 70px;
    }
  }

  .narrow .col .size {
    color: rgba(0, 0, 0, 0.67);
  }

  .empty-state,
  .loading-state {
    display: flex;
    height: 100%;
    flex-direction: column;
    place-content: center;
    align-items: center;
  }

  .empty-state {
    font-size: 12px;
    color: rgba(0, 0, 0, 0.34);

    p {
      width: 100%;
      margin: 8px 0;
      text-align: center;
    }
  }
</style>
