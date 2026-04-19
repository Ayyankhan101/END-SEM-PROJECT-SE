import { useEffect, useState } from 'react'
import { Layers, X } from 'lucide-react'
import api from '@/services/api'
import type { DockerImage, DockerVolume, DockerNetwork } from '@/types'

type Tab = 'images' | 'volumes' | 'networks'

export default function DockerResources() {
  const [activeTab, setActiveTab] = useState<Tab>('images')
  const [images, setImages] = useState<DockerImage[]>([])
  const [volumes, setVolumes] = useState<DockerVolume[]>([])
  const [networks, setNetworks] = useState<DockerNetwork[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [showPullForm, setShowPullForm] = useState(false)
  const [pullData, setPullData] = useState({ imageName: '', tag: 'latest' })
  const [pulling, setPulling] = useState(false)
  const [selectedImages, setSelectedImages] = useState<Set<string>>(new Set())
  const [showTagForm, setShowTagForm] = useState(false)
  const [tagData, setTagData] = useState({ imageId: '', newTag: '' })
  const [showHistoryModal, setShowHistoryModal] = useState(false)
  const [imageHistory, setImageHistory] = useState<any[]>([])
  const [historyLoading, setHistoryLoading] = useState(false)
  const [selectedImageId, setSelectedImageId] = useState('')

  useEffect(() => {
    loadData()
  }, [activeTab])

  async function loadData() {
    try {
      setLoading(true)
      if (activeTab === 'images') {
        setImages(await api.getImages())
      } else if (activeTab === 'volumes') {
        setVolumes(await api.getVolumes())
      } else {
        setNetworks(await api.getNetworks())
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load resources')
    } finally {
      setLoading(false)
    }
  }

  async function handlePull() {
    try {
      setPulling(true)
      await api.pullImage(pullData.imageName, pullData.tag)
      setShowPullForm(false)
      setPullData({ imageName: '', tag: 'latest' })
      loadData()
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to pull image')
    } finally {
      setPulling(false)
    }
  }

  async function handleDeleteImage(id: string) {
    if (!confirm('Delete this image?')) return
    try {
      await api.deleteImage(id, false)
      loadData()
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to delete image')
    }
  }

  async function handleShowHistory(imageId: string) {
    try {
      setSelectedImageId(imageId)
      setHistoryLoading(true)
      setShowHistoryModal(true)
      const history = await api.getImageHistory(imageId)
      setImageHistory(history)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load image history')
    } finally {
      setHistoryLoading(false)
    }
  }

  async function handleDeleteVolume(name: string) {
    if (!confirm('Delete this volume?')) return
    try {
      await api.deleteVolume(name, false)
      loadData()
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to delete volume')
    }
  }

  async function handleDeleteNetwork(id: string) {
    if (!confirm('Delete this network?')) return
    try {
      await api.deleteNetwork(id)
      loadData()
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to delete network')
    }
  }

  async function handleTagImage(imageId: string, newTag: string) {
    try {
      const image = images.find(i => i.id === imageId)
      if (!image) return
      
      const [oldRepo, oldTag = 'latest'] = image.tags[0]?.split(':') || [imageId, 'latest']
      
      await api.pullImage(oldRepo, oldTag)
      await api.tagImage(imageId, newTag)
      
      setShowTagForm(false)
      setTagData({ imageId: '', newTag: '' })
      loadData()
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to tag image')
    }
  }

  async function handleBulkDeleteImages() {
    if (!confirm(`Delete ${selectedImages.size} selected images?`)) return
    try {
      for (const id of selectedImages) {
        await api.deleteImage(id, true)
      }
      setSelectedImages(new Set())
      loadData()
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to delete images')
    }
  }

  const toggleImageSelect = (id: string) => {
    setSelectedImages(prev => {
      const newSet = new Set(prev)
      if (newSet.has(id)) newSet.delete(id)
      else newSet.add(id)
      return newSet
    })
  }

  function formatSize(bytes: number): string {
    if (bytes < 1024) return bytes + ' B'
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
    if (bytes < 1024 * 1024 * 1024) return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
    return (bytes / (1024 * 1024 * 1024)).toFixed(2) + ' GB'
  }

  const tabs: Tab[] = ['images', 'volumes', 'networks']

  return (
    <div className="p-6">
      <h1 className="text-2xl font-bold mb-6">Docker Resources</h1>

      {error && (
        <div className="bg-red-900/50 border border-red-500 text-red-200 px-4 py-2 rounded mb-4">
          {error}
        </div>
      )}

      <div className="flex gap-2 mb-6">
        {tabs.map(tab => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={`px-4 py-2 rounded ${
              activeTab === tab ? 'bg-blue-600' : 'bg-gray-800'
            }`}
          >
            {tab.charAt(0).toUpperCase() + tab.slice(1)}
          </button>
        ))}
      </div>

      {activeTab === 'images' && (
        <div className="mb-4">
          <button
            onClick={() => setShowPullForm(!showPullForm)}
            className="px-4 py-2 bg-blue-600 rounded hover:bg-blue-700"
          >
            {showPullForm ? 'Cancel' : 'Pull Image'}
          </button>

          {showPullForm && (
            <div className="mt-4 bg-gray-800 rounded p-4">
              <input
                type="text"
                placeholder="Image name"
                value={pullData.imageName}
                onChange={e => setPullData(d => ({ ...d, imageName: e.target.value }))}
                className="bg-gray-900 border border-gray-700 rounded px-3 py-2 mr-2"
              />
              <input
                type="text"
                placeholder="Tag"
                value={pullData.tag}
                onChange={e => setPullData(d => ({ ...d, tag: e.target.value }))}
                className="bg-gray-900 border border-gray-700 rounded px-3 py-2 mr-2 w-24"
              />
              <button
                onClick={handlePull}
                disabled={pulling || !pullData.imageName}
                className="px-4 py-2 bg-blue-600 rounded disabled:opacity-50"
              >
                {pulling ? 'Pulling...' : 'Pull'}
              </button>
            </div>
          )}
        </div>
      )}

      {loading ? (
        <div className="text-gray-400">Loading...</div>
      ) : activeTab === 'images' ? (
        <div>
          {selectedImages.size > 0 && (
            <div className="mb-4 flex items-center gap-4">
              <span className="text-gray-400">{selectedImages.size} selected</span>
              <button
                onClick={handleBulkDeleteImages}
                className="px-3 py-1.5 bg-red-900 rounded hover:bg-red-800 text-sm"
              >
                Delete Selected
              </button>
              <button
                onClick={() => setSelectedImages(new Set())}
                className="px-3 py-1.5 bg-gray-700 rounded hover:bg-gray-600 text-sm"
              >
                Clear Selection
              </button>
            </div>
          )}
          <div className="grid gap-4">
            {images.length === 0 ? (
              <div className="text-gray-400">No images found</div>
            ) : (
              images.map(img => (
                <div key={img.id} className="bg-gray-800 rounded-lg p-4">
                  <div className="flex justify-between items-start">
                    <div className="flex items-start gap-3">
                      <input
                        type="checkbox"
                        checked={selectedImages.has(img.id)}
                        onChange={() => toggleImageSelect(img.id)}
                        className="mt-2 w-4 h-4"
                      />
                      <div>
                        <div className="font-bold">{img.tags.join(', ') || img.id}</div>
                        <div className="text-gray-400 text-sm">
                          Size: {formatSize(img.size)} | Created: {new Date(img.created).toLocaleDateString()}
                        </div>
                        {img.tags.length > 0 && (
                          <div className="flex gap-2 mt-2">
                            {img.tags.slice(0, 5).map(tag => (
                              <span key={tag} className="text-xs bg-gray-700 px-2 py-0.5 rounded">{tag}</span>
                            ))}
                            {img.tags.length > 5 && (
                              <span className="text-xs text-gray-500">+{img.tags.length - 5} more</span>
                            )}
                          </div>
                        )}
                      </div>
                    </div>
                    <div className="flex gap-2">
                      <button
                        onClick={() => {
                          setTagData({ imageId: img.id, newTag: '' })
                          setShowTagForm(true)
                        }}
                        className="px-3 py-1 bg-gray-700 rounded hover:bg-gray-600 text-sm"
                      >
                        Tag
                      </button>
                      <button
                        onClick={() => handleShowHistory(img.id)}
                        className="px-3 py-1 bg-blue-900 rounded hover:bg-blue-800 text-sm"
                      >
                        History
                      </button>
                      <button
                        onClick={() => handleDeleteImage(img.id)}
                        className="px-3 py-1 bg-red-900 rounded hover:bg-red-800"
                      >
                        Delete
                      </button>
                    </div>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      ) : activeTab === 'volumes' ? (
        <div className="grid gap-4">
          {volumes.length === 0 ? (
            <div className="text-gray-400">No volumes found</div>
          ) : (
            volumes.map(vol => (
              <div key={vol.name} className="bg-gray-800 rounded-lg p-4">
                <div className="flex justify-between items-start">
                  <div>
                    <div className="font-bold">{vol.name}</div>
                    <div className="text-gray-400 text-sm">
                      Driver: {vol.driver} | Created: {vol.created}
                    </div>
                  </div>
                  <button
                    onClick={() => handleDeleteVolume(vol.name)}
                    className="px-3 py-1 bg-red-900 rounded hover:bg-red-800"
                  >
                    Delete
                  </button>
                </div>
              </div>
            ))
          )}
        </div>
      ) : (
        <div className="grid gap-4">
          {networks.length === 0 ? (
            <div className="text-gray-400">No networks found</div>
          ) : (
            networks.map(net => (
              <div key={net.id} className="bg-gray-800 rounded-lg p-4">
                <div className="flex justify-between items-start">
                  <div>
                    <div className="font-bold">{net.name}</div>
                    <div className="text-gray-400 text-sm">
                      Driver: {net.driver} | Scope: {net.scope}
                    </div>
                  </div>
                  <button
                    onClick={() => handleDeleteNetwork(net.id)}
                    className="px-3 py-1 bg-red-900 rounded hover:bg-red-800"
                  >
                    Delete
                  </button>
                </div>
              </div>
            ))
          )}
        </div>
      )}

      {showTagForm && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-gray-800 p-6 rounded-lg w-96">
            <h3 className="text-lg font-bold mb-4">Tag Image</h3>
            <div className="mb-4">
              <label className="block text-sm text-gray-400 mb-1">New Tag</label>
              <input
                type="text"
                value={tagData.newTag}
                onChange={e => setTagData(d => ({ ...d, newTag: e.target.value }))}
                placeholder="my-repo:my-tag"
                className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2"
              />
            </div>
            <div className="flex justify-end gap-3">
              <button
                onClick={() => {
                  setShowTagForm(false)
                  setTagData({ imageId: '', newTag: '' })
                }}
                className="px-4 py-2 bg-gray-700 rounded"
              >
                Cancel
              </button>
              <button
                onClick={() => handleTagImage(tagData.imageId, tagData.newTag)}
                disabled={!tagData.newTag}
                className="px-4 py-2 bg-blue-600 rounded disabled:opacity-50"
              >
                Tag
              </button>
            </div>
</div>
          </div>
        )}

      {showHistoryModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-gray-800 p-6 rounded-lg w-[600px] max-h-[80vh] overflow-auto">
            <div className="flex justify-between items-center mb-4">
              <h3 className="text-lg font-bold flex items-center gap-2">
                <Layers className="w-5 h-5" />
                Image History
              </h3>
              <button onClick={() => setShowHistoryModal(false)} className="text-gray-400 hover:text-white">
                <X className="w-5 h-5" />
              </button>
            </div>
            {historyLoading ? (
              <div className="text-gray-400">Loading history...</div>
            ) : (
              <table className="w-full">
                <thead className="bg-gray-700">
                  <tr>
                    <th className="px-3 py-2 text-left text-sm">Layer</th>
                    <th className="px-3 py-2 text-left text-sm">Created</th>
                    <th className="px-3 py-2 text-left text-sm">Size</th>
                  </tr>
                </thead>
                <tbody>
                  {imageHistory.map((layer: any, idx: number) => (
                    <tr key={idx} className="border-t border-gray-700">
                      <td className="px-3 py-2 text-sm font-mono text-blue-400">
                        {layer.created_by?.substring(0, 50) || layer.id?.substring(0, 12) || 'N/A'}
                      </td>
                      <td className="px-3 py-2 text-sm text-gray-400">
                        {layer.created ? new Date(layer.created).toLocaleString() : '-'}
                      </td>
                      <td className="px-3 py-2 text-sm text-gray-400">
                        {formatSize(layer.size)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </div>
      )}
    </div>
  )
}