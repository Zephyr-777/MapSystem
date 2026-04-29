import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import InfoPanel from '../InfoPanel.vue'

const mocks = vi.hoisted(() => ({
  fetchPreviewBlob: vi.fn(),
  download: vi.fn(),
  downloadBatch: vi.fn(),
  getNetCDFSlice: vi.fn(),
  createObjectURL: vi.fn(),
  revokeObjectURL: vi.fn(),
  warning: vi.fn(),
  success: vi.fn(),
  error: vi.fn(),
}))

vi.mock('@/api/geodata', () => ({
  geoDataApi: {
    fetchPreviewBlob: mocks.fetchPreviewBlob,
    download: mocks.download,
    downloadBatch: mocks.downloadBatch,
    getNetCDFSlice: mocks.getNetCDFSlice,
  },
}))

vi.mock('@/stores/auth', () => ({
  useAuthStore: () => ({
    user: { role: 'admin' },
  }),
}))

vi.mock('element-plus', () => ({
  ElMessage: {
    warning: mocks.warning,
    success: mocks.success,
    error: mocks.error,
  },
}))

vi.mock('@element-plus/icons-vue', () => {
  const iconStub = { template: '<span />' }
  return {
    Close: iconStub,
    Picture: iconStub,
    PictureFilled: iconStub,
    Download: iconStub,
    View: iconStub,
    Location: iconStub,
    Document: iconStub,
    ArrowRight: iconStub,
    Share: iconStub,
    DataBoard: iconStub,
    Loading: iconStub,
    Edit: iconStub,
    Check: iconStub,
    Link: iconStub,
    FullScreen: iconStub,
  }
})

describe('InfoPanel.vue', () => {
  const feature = {
    id: 1,
    name: '示例 GeoTIFF',
    type: 'GeoTIFF',
    sub_type: 'GeoTIFF',
    file_path: 'demo/sample.tif',
    uploadTime: '2026-04-21 12:00:00',
    center_x: 116.4,
    center_y: 39.9,
  }

  beforeEach(() => {
    vi.clearAllMocks()
    mocks.createObjectURL.mockReturnValue('blob:preview-url')
    mocks.revokeObjectURL.mockImplementation(() => undefined)
    global.URL.createObjectURL = mocks.createObjectURL
    global.URL.revokeObjectURL = mocks.revokeObjectURL
  })

  function mountPanel() {
    return mount(InfoPanel, {
      props: {
        visible: true,
        title: '详情',
        feature,
        isMultiSelection: false,
        selectedItems: [],
      },
      global: {
        stubs: {
          Transition: false,
          'el-icon': { template: '<i><slot /></i>' },
          'el-image': {
            props: ['src'],
            template: '<img class="el-image-stub" :src="src" />',
          },
          'el-dialog': {
            props: ['modelValue'],
            template: '<div v-if="modelValue" class="el-dialog-stub"><slot /><slot name="footer" /></div>',
          },
          'el-button': {
            emits: ['click'],
            template: '<button @click="$emit(\'click\')"><slot /></button>',
          },
          'el-input': {
            template: '<input />',
          },
        },
      },
    })
  }

  it('loads preview blob for tif features and renders object url', async () => {
    mocks.fetchPreviewBlob.mockResolvedValueOnce(new Blob(['preview'], { type: 'image/png' }))

    const wrapper = mountPanel()
    await flushPromises()

    expect(mocks.fetchPreviewBlob).toHaveBeenCalledWith(1)
    expect(wrapper.find('.el-image-stub').attributes('src')).toBe('blob:preview-url')
    expect(wrapper.text()).not.toContain('暂无预览图')
  })

  it('shows empty state when preview file is missing', async () => {
    mocks.fetchPreviewBlob.mockRejectedValueOnce({ response: { status: 404 } })

    const wrapper = mountPanel()
    await flushPromises()

    expect(wrapper.text()).toContain('暂无预览图')
  })

  it('revokes generated object urls on unmount', async () => {
    mocks.fetchPreviewBlob.mockResolvedValueOnce(new Blob(['preview'], { type: 'image/png' }))

    const wrapper = mountPanel()
    await flushPromises()
    wrapper.unmount()

    expect(mocks.revokeObjectURL).toHaveBeenCalledWith('blob:preview-url')
  })
})
