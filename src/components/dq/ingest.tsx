'use client'

import { useEffect, useState, useRef, useCallback } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  Upload,
  FileText,
  FileSpreadsheet,
  CheckCircle2,
  AlertCircle,
  X,
  Loader2,
  ArrowRight,
  Table2,
  Database,
  Clock,
  Info,
} from 'lucide-react'
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  CardDescription,
} from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Badge } from '@/components/ui/badge'
import { Progress } from '@/components/ui/progress'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { useAppStore } from '@/lib/store'
import { toast } from 'sonner'

// ── Constants ──
const CHUNK_SIZE = 5 * 1024 * 1024 // 5MB
const MAX_FILE_SIZE = 100 * 1024 * 1024 // 100MB
const SUPPORTED_EXTENSIONS = ['.csv', '.json', '.xlsx', '.xls']

type UploadState = 'idle' | 'selected' | 'uploading' | 'success' | 'error'

interface RecentUpload {
  id: string
  name: string
  service: { name: string; platform: string }
  rowCount: number
  columnCount: number
  qualityScore: number
  createdAt: string
}

// ── Helpers ──
function formatBytes(bytes: number): string {
  if (bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(1))} ${sizes[i]}`
}

function getFileExtension(filename: string): string {
  const parts = filename.split('.')
  return parts.length > 1 ? `.${parts[parts.length - 1].toLowerCase()}` : ''
}

function getTableNameFromFilename(filename: string): string {
  const nameWithoutExt = filename.replace(/\.[^/.]+$/, '')
  return (
    nameWithoutExt
      .replace(/[^a-zA-Z0-9_]/g, '_')
      .replace(/_+/g, '_')
      .replace(/^_|_$/g, '')
      .toLowerCase() || 'untitled_table'
  )
}

function getFileTypeIcon(ext: string) {
  if (ext === '.csv' || ext === '.json') return FileText
  if (ext === '.xlsx' || ext === '.xls') return FileSpreadsheet
  return FileText
}

function getFileTypeColor(ext: string) {
  if (ext === '.csv') return 'bg-emerald-100 text-emerald-700'
  if (ext === '.json') return 'bg-amber-100 text-amber-700'
  if (ext === '.xlsx' || ext === '.xls') return 'bg-sky-100 text-sky-700'
  return 'bg-slate-100 text-slate-600'
}

// ── Step Indicator ──
function StepIndicator({ currentStep }: { currentStep: number }) {
  const steps = [
    { num: 1, label: 'Select File' },
    { num: 2, label: 'Configure' },
    { num: 3, label: 'Upload' },
    { num: 4, label: 'Complete' },
  ]

  return (
    <div className="flex items-center gap-1 sm:gap-2 mb-6">
      {steps.map((step, idx) => {
        const isActive = step.num === currentStep
        const isCompleted = step.num < currentStep
        return (
          <div key={step.num} className="flex items-center gap-1 sm:gap-2 flex-1">
            <div className="flex items-center gap-1.5">
              <div
                className={`flex h-7 w-7 items-center justify-center rounded-full text-xs font-semibold transition-colors ${
                  isCompleted
                    ? 'bg-emerald-500 text-white'
                    : isActive
                      ? 'bg-emerald-100 text-emerald-700 ring-2 ring-emerald-500 ring-offset-1'
                      : 'bg-slate-100 text-slate-400'
                }`}
              >
                {isCompleted ? <CheckCircle2 className="h-4 w-4" /> : step.num}
              </div>
              <span
                className={`text-xs font-medium hidden sm:inline ${
                  isActive ? 'text-slate-900' : 'text-slate-400'
                }`}
              >
                {step.label}
              </span>
            </div>
            {idx < steps.length - 1 && (
              <div
                className={`flex-1 h-0.5 rounded-full transition-colors ${
                  isCompleted ? 'bg-emerald-400' : 'bg-slate-200'
                }`}
              />
            )}
          </div>
        )
      })}
    </div>
  )
}

// ── Upload Instructions Panel ──
function InstructionsPanel() {
  return (
    <div className="grid gap-4 md:grid-cols-2">
      {/* Steps */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base flex items-center gap-2">
            <Info className="h-4 w-4 text-slate-500" />
            How to Upload
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-3">
            {[
              { step: 1, text: 'Prepare your data file (CSV, JSON, or Excel)' },
              { step: 2, text: 'Drag and drop or click to select your file' },
              { step: 3, text: 'Configure table name and service name' },
              { step: 4, text: 'Click upload and monitor progress' },
              { step: 5, text: 'Data is automatically profiled and quality checked' },
            ].map((item) => (
              <div key={item.step} className="flex items-start gap-3">
                <div className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-slate-100 text-xs font-semibold text-slate-600">
                  {item.step}
                </div>
                <p className="text-sm text-slate-600 pt-0.5">{item.text}</p>
              </div>
            ))}
          </div>

          <div className="flex items-start gap-2 rounded-lg bg-amber-50 border border-amber-200 p-3 mt-4">
            <AlertCircle className="h-4 w-4 text-amber-600 shrink-0 mt-0.5" />
            <div className="text-xs text-amber-700">
              <p className="font-medium mb-0.5">Tip</p>
              <p>
                For large files (&gt;10MB), uploads are automatically chunked
                for reliability.
              </p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Supported Formats */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base">Supported Formats</CardTitle>
          <CardDescription>
            Each file type has specific requirements
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {/* CSV */}
          <div className="rounded-lg border border-slate-200 p-3">
            <div className="flex items-center gap-2 mb-2">
              <Badge className={getFileTypeColor('.csv')}>.csv</Badge>
              <span className="text-sm font-medium text-slate-700">CSV</span>
            </div>
            <p className="text-xs text-slate-500 mb-2">
              Comma-separated values with headers
            </p>
            <pre className="bg-slate-50 rounded p-2 text-[11px] text-slate-600 overflow-x-auto font-mono">
              {`id,name,email,created_at
1,John Doe,john@example.com,2024-01-15
2,Jane Smith,jane@example.com,2024-01-16`}
            </pre>
          </div>

          {/* JSON */}
          <div className="rounded-lg border border-slate-200 p-3">
            <div className="flex items-center gap-2 mb-2">
              <Badge className={getFileTypeColor('.json')}>.json</Badge>
              <span className="text-sm font-medium text-slate-700">JSON</span>
            </div>
            <p className="text-xs text-slate-500 mb-2">
              Array of objects with consistent keys
            </p>
            <pre className="bg-slate-50 rounded p-2 text-[11px] text-slate-600 overflow-x-auto font-mono">
              {`[{"id": 1, "name": "John Doe"},
 {"id": 2, "name": "Jane Smith"}]`}
            </pre>
          </div>

          {/* Excel */}
          <div className="rounded-lg border border-slate-200 p-3">
            <div className="flex items-center gap-2 mb-2">
              <Badge className={getFileTypeColor('.xlsx')}>.xlsx</Badge>
              <Badge className={getFileTypeColor('.xls')}>.xls</Badge>
              <span className="text-sm font-medium text-slate-700">Excel</span>
            </div>
            <p className="text-xs text-slate-500">
              First row must contain column headers. Only the first sheet is
              processed.
            </p>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}

// ── Main Component ──
export default function Ingest() {
  const setCurrentView = useAppStore((s) => s.setCurrentView)

  const safeFixed = (val: number | undefined | null, d = 1) => (val ?? 0).toFixed(d)

  // State
  const [uploadState, setUploadState] = useState<UploadState>('idle')
  const [isDragging, setIsDragging] = useState(false)
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [tableName, setTableName] = useState('')
  const [serviceName, setServiceName] = useState('File Uploads')
  const [progress, setProgress] = useState(0)
  const [bytesUploaded, setBytesUploaded] = useState(0)
  const [currentChunk, setCurrentChunk] = useState(0)
  const [totalChunks, setTotalChunks] = useState(0)
  const [recentUploads, setRecentUploads] = useState<RecentUpload[]>([])
  const [uploadsLoading, setUploadsLoading] = useState(false)
  const [errorMessage, setErrorMessage] = useState('')

  const fileInputRef = useRef<HTMLInputElement>(null)

  // Determine current step from upload state
  const currentStep =
    uploadState === 'idle'
      ? 1
      : uploadState === 'selected'
        ? 2
        : uploadState === 'uploading'
          ? 3
          : uploadState === 'success'
            ? 4
            : 2

  // Fetch recent uploads on mount and after successful upload
  const fetchRecentUploads = useCallback(async () => {
    setUploadsLoading(true)
    try {
      const res = await fetch('/api/tables?sort=name&limit=50')
      if (res.ok) {
        const allTablesRaw: RecentUpload[] = await res.json()
        const allTables = Array.isArray(allTablesRaw) ? allTablesRaw : []
        const fileUploads = allTables.filter(
          (t) => t.service?.platform === 'file_upload'
        )
        setRecentUploads(fileUploads)
      }
    } catch {
      // silent fail
    } finally {
      setUploadsLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchRecentUploads()
  }, [fetchRecentUploads])

  // ── File handling ──
  function validateFile(file: File): string | null {
    const ext = getFileExtension(file.name)
    if (!SUPPORTED_EXTENSIONS.includes(ext)) {
      return `Unsupported file type "${ext}". Please use CSV, JSON, or Excel files.`
    }
    if (file.size > MAX_FILE_SIZE) {
      return `File size (${formatBytes(file.size)}) exceeds the 100MB limit.`
    }
    if (file.size === 0) {
      return 'File is empty. Please select a valid data file.'
    }
    return null
  }

  function handleFileSelect(file: File) {
    const error = validateFile(file)
    if (error) {
      toast.error('Invalid File', { description: error })
      return
    }

    setSelectedFile(file)
    setTableName(getTableNameFromFilename(file.name))
    setUploadState('selected')
    setErrorMessage('')
    setProgress(0)
    setBytesUploaded(0)
  }

  function handleDragOver(e: React.DragEvent) {
    e.preventDefault()
    e.stopPropagation()
    setIsDragging(true)
  }

  function handleDragLeave(e: React.DragEvent) {
    e.preventDefault()
    e.stopPropagation()
    setIsDragging(false)
  }

  function handleDrop(e: React.DragEvent) {
    e.preventDefault()
    e.stopPropagation()
    setIsDragging(false)

    const files = e.dataTransfer.files
    if (files.length > 0) {
      handleFileSelect(files[0])
    }
  }

  function handleFileInputChange(e: React.ChangeEvent<HTMLInputElement>) {
    const files = e.target.files
    if (files && files.length > 0) {
      handleFileSelect(files[0])
    }
  }

  function handleClear() {
    setSelectedFile(null)
    setTableName('')
    setServiceName('File Uploads')
    setUploadState('idle')
    setProgress(0)
    setBytesUploaded(0)
    setCurrentChunk(0)
    setTotalChunks(0)
    setErrorMessage('')
    if (fileInputRef.current) {
      fileInputRef.current.value = ''
    }
  }

  // ── Upload ──
  async function handleUpload() {
    if (!selectedFile || !tableName.trim()) return

    setUploadState('uploading')
    setProgress(0)
    setBytesUploaded(0)
    setErrorMessage('')

    const fileId = `${Date.now()}-${Math.random().toString(36).slice(2, 9)}`
    const fileName = selectedFile.name
    const isChunked = selectedFile.size > 10 * 1024 * 1024

    if (isChunked) {
      const chunks = Math.ceil(selectedFile.size / CHUNK_SIZE)
      setTotalChunks(chunks)

      try {
        for (let i = 0; i < chunks; i++) {
          setCurrentChunk(i + 1)
          const chunk = selectedFile.slice(
            i * CHUNK_SIZE,
            (i + 1) * CHUNK_SIZE
          )
          const formData = new FormData()
          formData.append('file', chunk)
          formData.append('chunkIndex', String(i))
          formData.append('totalChunks', String(chunks))
          formData.append('fileId', fileId)
          formData.append('fileName', fileName)
          formData.append('tableName', tableName.trim())
          formData.append('serviceName', serviceName.trim())

          const res = await fetch('/api/ingest', {
            method: 'POST',
            body: formData,
          })

          if (!res.ok) {
            const errData = await res.json().catch(() => ({}))
            throw new Error(
              errData.error || `Upload failed at chunk ${i + 1}`
            )
          }

          const uploaded = Math.min(
            (i + 1) * CHUNK_SIZE,
            selectedFile.size
          )
          setBytesUploaded(uploaded)
          setProgress(Math.round((uploaded / selectedFile.size) * 100))
        }
        setUploadState('success')
        toast.success('Upload Complete', {
          description: `${fileName} has been uploaded and profiled successfully.`,
        })
        fetchRecentUploads()
      } catch (err) {
        const message =
          err instanceof Error ? err.message : 'Upload failed'
        setErrorMessage(message)
        setUploadState('error')
        toast.error('Upload Failed', { description: message })
      }
    } else {
      try {
        const formData = new FormData()
        formData.append('file', selectedFile)
        formData.append('fileName', fileName)
        formData.append('tableName', tableName.trim())
        formData.append('serviceName', serviceName.trim())

        // Simulate progress for single upload
        setProgress(30)

        const res = await fetch('/api/ingest', {
          method: 'POST',
          body: formData,
        })

        if (!res.ok) {
          const errData = await res.json().catch(() => ({}))
          throw new Error(errData.error || 'Upload failed')
        }

        setBytesUploaded(selectedFile.size)
        setProgress(100)
        setUploadState('success')
        toast.success('Upload Complete', {
          description: `${fileName} has been uploaded and profiled successfully.`,
        })
        fetchRecentUploads()
      } catch (err) {
        const message =
          err instanceof Error ? err.message : 'Upload failed'
        setErrorMessage(message)
        setUploadState('error')
        toast.error('Upload Failed', { description: message })
      }
    }
  }

  // ── Score badge color ──
  function scoreBadge(score: number) {
    if (score >= 90) return 'bg-emerald-100 text-emerald-700'
    if (score >= 70) return 'bg-amber-100 text-amber-700'
    return 'bg-red-100 text-red-700'
  }

  // ── Render ──
  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h2 className="text-xl font-semibold text-slate-900">Ingest Data</h2>
        <p className="text-sm text-slate-500">
          Upload files to create new tables with automatic profiling
        </p>
      </div>

      {/* Step Indicator */}
      {uploadState !== 'idle' && <StepIndicator currentStep={currentStep} />}

      {/* Upload Zone */}
      <AnimatePresence mode="wait">
        {uploadState === 'idle' && (
          <motion.div
            key="dropzone"
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            transition={{ duration: 0.2 }}
          >
            <motion.div
              onDragOver={handleDragOver}
              onDragLeave={handleDragLeave}
              onDrop={handleDrop}
              onClick={() => fileInputRef.current?.click()}
              className={`relative cursor-pointer rounded-xl border-2 border-dashed p-8 sm:p-12 text-center transition-all duration-200 ${
                isDragging
                  ? 'border-emerald-400 bg-emerald-50/80 scale-[1.01]'
                  : 'border-slate-300 bg-white hover:border-emerald-300 hover:bg-gradient-to-b hover:from-emerald-50/40 hover:to-white'
              }`}
              whileHover={{ scale: 1.005 }}
              whileTap={{ scale: 0.995 }}
            >
              <input
                ref={fileInputRef}
                type="file"
                accept=".csv,.json,.xlsx,.xls"
                className="hidden"
                onChange={handleFileInputChange}
              />

              <motion.div
                animate={{
                  scale: isDragging ? 1.1 : 1,
                  y: isDragging ? -4 : 0,
                }}
                transition={{
                  type: 'spring',
                  stiffness: 300,
                  damping: 20,
                }}
                className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-2xl bg-slate-100"
              >
                <Upload
                  className={`h-8 w-8 transition-colors ${
                    isDragging ? 'text-emerald-500' : 'text-slate-400'
                  }`}
                />
              </motion.div>

              <p className="text-base font-medium text-slate-700 mb-1">
                {isDragging
                  ? 'Drop your file here'
                  : 'Drag & drop your file here'}
              </p>
              <p className="text-sm text-slate-400 mb-4">
                or{' '}
                <span className="text-emerald-600 font-medium">browse</span> to
                choose
              </p>

              <div className="flex flex-wrap items-center justify-center gap-2 mb-4">
                {[
                  { ext: '.csv', icon: FileText, color: 'text-emerald-600' },
                  {
                    ext: '.json',
                    icon: FileText,
                    color: 'text-amber-600',
                  },
                  {
                    ext: '.xlsx',
                    icon: FileSpreadsheet,
                    color: 'text-sky-600',
                  },
                  {
                    ext: '.xls',
                    icon: FileSpreadsheet,
                    color: 'text-sky-600',
                  },
                ].map((fmt) => (
                  <div
                    key={fmt.ext}
                    className="flex items-center gap-1.5 rounded-full bg-slate-100 px-3 py-1"
                  >
                    <fmt.icon className={`h-3.5 w-3.5 ${fmt.color}`} />
                    <span className="text-xs font-medium text-slate-600">
                      {fmt.ext}
                    </span>
                  </div>
                ))}
              </div>

              <p className="text-xs text-slate-400">
                Maximum file size: <span className="font-medium">100MB</span>
              </p>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* File Configuration Panel */}
      <AnimatePresence>
        {(uploadState === 'selected' ||
          uploadState === 'uploading' ||
          uploadState === 'error') &&
          selectedFile && (
            <motion.div
              key="config"
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              transition={{ duration: 0.2 }}
            >
              <Card>
                <CardHeader className="pb-3">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <div
                        className={`rounded-lg p-2 ${getFileTypeColor(getFileExtension(selectedFile.name))}`}
                      >
                        {(() => {
                          const Icon = getFileTypeIcon(
                            getFileExtension(selectedFile.name)
                          )
                          return <Icon className="h-5 w-5" />
                        })()}
                      </div>
                      <div>
                        <CardTitle className="text-base">
                          {selectedFile.name}
                        </CardTitle>
                        <CardDescription>
                          {formatBytes(selectedFile.size)} &middot;{' '}
                          {getFileExtension(selectedFile.name)
                            .toUpperCase()
                            .slice(1)}
                        </CardDescription>
                      </div>
                    </div>
                    {uploadState === 'selected' && (
                      <Button
                        variant="ghost"
                        size="icon"
                        className="h-8 w-8 text-slate-400 hover:text-slate-600"
                        onClick={handleClear}
                      >
                        <X className="h-4 w-4" />
                      </Button>
                    )}
                  </div>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="grid gap-4 sm:grid-cols-2">
                    <div className="space-y-2">
                      <Label htmlFor="tableName">Table Name</Label>
                      <Input
                        id="tableName"
                        value={tableName}
                        onChange={(e) => setTableName(e.target.value)}
                        placeholder="my_table"
                        disabled={uploadState === 'uploading'}
                        className="font-mono text-sm"
                      />
                      <p className="text-xs text-slate-400">
                        Auto-generated from filename
                      </p>
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="serviceName">Service Name</Label>
                      <Input
                        id="serviceName"
                        value={serviceName}
                        onChange={(e) => setServiceName(e.target.value)}
                        placeholder="File Uploads"
                        disabled={uploadState === 'uploading'}
                      />
                    </div>
                  </div>

                  {/* Progress Bar */}
                  {uploadState === 'uploading' && (
                    <motion.div
                      initial={{ opacity: 0 }}
                      animate={{ opacity: 1 }}
                      className="space-y-3"
                    >
                      <div className="flex items-center justify-between text-sm">
                        <span className="text-slate-600 font-medium">
                          Uploading...
                        </span>
                        <span className="text-emerald-600 font-semibold">
                          {progress}%
                        </span>
                      </div>
                      <div className="relative">
                        <Progress value={progress} className="h-2.5 [&>div]:bg-emerald-500" />
                      </div>
                      <div className="flex items-center justify-between text-xs text-slate-400">
                        <span>
                          {formatBytes(bytesUploaded)} /{' '}
                          {formatBytes(selectedFile.size)}
                        </span>
                        {totalChunks > 0 && (
                          <span>
                            Chunk {currentChunk} of {totalChunks}
                          </span>
                        )}
                      </div>
                    </motion.div>
                  )}

                  {/* Error message */}
                  {uploadState === 'error' && errorMessage && (
                    <motion.div
                      initial={{ opacity: 0 }}
                      animate={{ opacity: 1 }}
                      className="flex items-start gap-2 rounded-lg bg-red-50 border border-red-200 p-3"
                    >
                      <AlertCircle className="h-4 w-4 text-red-500 shrink-0 mt-0.5" />
                      <div>
                        <p className="text-sm font-medium text-red-700">
                          Upload Failed
                        </p>
                        <p className="text-xs text-red-600 mt-0.5">
                          {errorMessage}
                        </p>
                      </div>
                    </motion.div>
                  )}

                  {/* Action buttons */}
                  <div className="flex items-center gap-3 pt-2">
                    {uploadState === 'selected' && (
                      <>
                        <Button
                          onClick={handleUpload}
                          disabled={
                            !tableName.trim() ||
                            uploadState === 'uploading'
                          }
                          className="bg-emerald-600 hover:bg-emerald-700 text-white"
                        >
                          <Upload className="h-4 w-4 mr-2" />
                          Start Upload
                        </Button>
                        <Button variant="outline" onClick={handleClear}>
                          Cancel
                        </Button>
                      </>
                    )}
                    {uploadState === 'uploading' && (
                      <div className="flex items-center gap-2 text-sm text-slate-500">
                        <Loader2 className="h-4 w-4 animate-spin text-emerald-500" />
                        <span>
                          {totalChunks > 0
                            ? `Uploading chunk ${currentChunk} of ${totalChunks}...`
                            : 'Uploading file...'}
                        </span>
                      </div>
                    )}
                    {uploadState === 'error' && (
                      <div className="flex items-center gap-3">
                        <Button
                          onClick={handleUpload}
                          className="bg-emerald-600 hover:bg-emerald-700 text-white"
                        >
                          <Upload className="h-4 w-4 mr-2" />
                          Retry Upload
                        </Button>
                        <Button variant="outline" onClick={handleClear}>
                          Cancel
                        </Button>
                      </div>
                    )}
                  </div>
                </CardContent>
              </Card>
            </motion.div>
          )}
      </AnimatePresence>

      {/* Success Panel */}
      <AnimatePresence>
        {uploadState === 'success' && (
          <motion.div
            key="success"
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.95 }}
            transition={{ duration: 0.3 }}
          >
            <Card className="border-emerald-200 bg-emerald-50/50">
              <CardContent className="p-6">
                <div className="flex items-start gap-4">
                  <motion.div
                    initial={{ scale: 0 }}
                    animate={{ scale: 1 }}
                    transition={{
                      type: 'spring',
                      stiffness: 300,
                      damping: 20,
                      delay: 0.1,
                    }}
                  >
                    <CheckCircle2 className="h-10 w-10 text-emerald-500" />
                  </motion.div>
                  <div className="flex-1">
                    <h3 className="text-lg font-semibold text-slate-900 mb-1">
                      Upload Successful!
                    </h3>
                    <p className="text-sm text-slate-600 mb-4">
                      {selectedFile?.name} has been uploaded and is being
                      profiled. Quality checks will run automatically.
                    </p>
                    <div className="flex items-center gap-3 flex-wrap">
                      <Button
                        onClick={() => {
                          handleClear()
                        }}
                        className="bg-emerald-600 hover:bg-emerald-700 text-white"
                      >
                        <Upload className="h-4 w-4 mr-2" />
                        Upload Another
                      </Button>
                      <Button
                        variant="outline"
                        onClick={() => setCurrentView('tables')}
                      >
                        <Table2 className="h-4 w-4 mr-2" />
                        View in Tables
                      </Button>
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Recent Uploads Table */}
      {recentUploads.length > 0 && (
        <Card>
          <CardHeader className="pb-3">
            <div className="flex items-center justify-between">
              <CardTitle className="text-base flex items-center gap-2">
                <Database className="h-4 w-4 text-slate-500" />
                Recent File Uploads
              </CardTitle>
              <Button
                variant="ghost"
                size="sm"
                className="text-emerald-600 hover:text-emerald-700"
                onClick={() => setCurrentView('tables')}
              >
                View All Tables
                <ArrowRight className="h-4 w-4 ml-1" />
              </Button>
            </div>
            <CardDescription>
              {recentUploads.length} table
              {recentUploads.length !== 1 ? 's' : ''} from file uploads
            </CardDescription>
          </CardHeader>
          <CardContent className="p-0">
            <div className="max-h-96 overflow-y-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Table Name</TableHead>
                    <TableHead className="hidden sm:table-cell">
                      Service
                    </TableHead>
                    <TableHead className="hidden md:table-cell text-right">
                      Rows
                    </TableHead>
                    <TableHead className="hidden md:table-cell text-right">
                      Columns
                    </TableHead>
                    <TableHead>Quality</TableHead>
                    <TableHead className="hidden lg:table-cell">
                      Upload Time
                    </TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {uploadsLoading ? (
                    Array.from({ length: 3 }).map((_, i) => (
                      <TableRow key={i}>
                        <TableCell colSpan={6} className="py-2">
                          <div className="h-5 bg-slate-100 rounded animate-pulse" />
                        </TableCell>
                      </TableRow>
                    ))
                  ) : (
                    recentUploads.map((upload) => (
                      <TableRow
                        key={upload.id}
                        className="cursor-pointer hover:bg-slate-50"
                        onClick={() => setCurrentView('tables')}
                      >
                        <TableCell>
                          <div className="flex items-center gap-2">
                            <FileSpreadsheet className="h-4 w-4 text-slate-400 shrink-0" />
                            <span className="font-medium text-slate-900 text-sm">
                              {upload.name}
                            </span>
                          </div>
                        </TableCell>
                        <TableCell className="hidden sm:table-cell">
                          <Badge variant="outline" className="text-xs">
                            <Database className="h-3 w-3 mr-1" />
                            {upload.service?.name}
                          </Badge>
                        </TableCell>
                        <TableCell className="hidden md:table-cell text-right text-sm text-slate-600">
                          {upload.rowCount.toLocaleString()}
                        </TableCell>
                        <TableCell className="hidden md:table-cell text-right text-sm text-slate-600">
                          {upload.columnCount}
                        </TableCell>
                        <TableCell>
                          <Badge className={scoreBadge(upload.qualityScore)}>
                            {safeFixed(upload.qualityScore)}%
                          </Badge>
                        </TableCell>
                        <TableCell className="hidden lg:table-cell text-xs text-slate-400">
                          <div className="flex items-center gap-1">
                            <Clock className="h-3 w-3" />
                            {new Date(upload.createdAt).toLocaleString()}
                          </div>
                        </TableCell>
                      </TableRow>
                    ))
                  )}
                </TableBody>
              </Table>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Instructions Panel (shown when idle) */}
      {uploadState === 'idle' && <InstructionsPanel />}
    </div>
  )
}
