'use client'

import { Tag, Plus, Search } from 'lucide-react'
import { Card, CardContent } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { useEffect, useState } from 'react'

interface TagItem {
  id: string
  name: string
  displayName: string | null
  description: string | null
  color: string
  tagFQN: string | null
  usageCount: number
}

interface GlossaryTerm {
  id: string
  name: string
  qualifiedName: string
  description: string | null
  definition: string | null
  category: string | null
  status: string
}

export default function Governance() {
  const [tags, setTags] = useState<TagItem[]>([])
  const [terms, setTerms] = useState<GlossaryTerm[]>([])
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')
  const [activeTab, setActiveTab] = useState<'tags' | 'glossary'>('tags')

  useEffect(() => {
    Promise.all([
      fetch('/api/tags').then((r) => r.json()).catch(() => []),
      fetch('/api/glossary').then((r) => r.json()).catch(() => []),
    ])
      .then(([t, g]) => {
        setTags(Array.isArray(t) ? t : [])
        setTerms(Array.isArray(g) ? g : [])
      })
      .finally(() => setLoading(false))
  }, [])

  const filteredTags = tags.filter(
    (t) =>
      t.name.toLowerCase().includes(search.toLowerCase()) ||
      (t.displayName || '').toLowerCase().includes(search.toLowerCase())
  )

  const filteredTerms = terms.filter(
    (t) =>
      t.name.toLowerCase().includes(search.toLowerCase()) ||
      (t.description || '').toLowerCase().includes(search.toLowerCase())
  )

  const statusColors: Record<string, string> = {
    approved: 'bg-emerald-100 text-emerald-700',
    draft: 'bg-amber-100 text-amber-700',
    deprecated: 'bg-slate-100 text-slate-600',
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h2 className="text-xl font-semibold text-slate-900">Governance</h2>
          <p className="text-sm text-slate-500">
            {tags.length} tags &middot; {terms.length} glossary terms
          </p>
        </div>
        <Button>
          <Plus className="h-4 w-4 mr-2" />
          Add {activeTab === 'tags' ? 'Tag' : 'Term'}
        </Button>
      </div>

      {/* Tab switcher */}
      <div className="flex gap-1 border-b">
        <Button
          variant={activeTab === 'tags' ? 'default' : 'ghost'}
          size="sm"
          onClick={() => setActiveTab('tags')}
        >
          <Tag className="h-4 w-4 mr-2" />
          Tags
        </Button>
        <Button
          variant={activeTab === 'glossary' ? 'default' : 'ghost'}
          size="sm"
          onClick={() => setActiveTab('glossary')}
        >
          Tags & Glossary
        </Button>
      </div>

      <div className="relative max-w-sm">
        <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
        <Input
          placeholder={activeTab === 'tags' ? 'Search tags...' : 'Search glossary...'}
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="pl-9"
        />
      </div>

      {activeTab === 'tags' ? (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {filteredTags.map((tag) => (
            <Card key={tag.id} className="hover:shadow-md transition-shadow cursor-pointer">
              <CardContent className="p-5">
                <div className="flex items-center gap-3 mb-2">
                  <span
                    className="h-3 w-3 rounded-full shrink-0"
                    style={{ backgroundColor: tag.color }}
                  />
                  <div>
                    <h3 className="font-semibold text-slate-900">
                      {tag.displayName || tag.name}
                    </h3>
                    {tag.tagFQN && (
                      <p className="text-xs text-slate-400 font-mono">{tag.tagFQN}</p>
                    )}
                  </div>
                </div>
                {tag.description && (
                  <p className="text-sm text-slate-500 line-clamp-2 mb-2">{tag.description}</p>
                )}
                <Badge variant="secondary" className="text-xs">
                  {tag.usageCount} uses
                </Badge>
              </CardContent>
            </Card>
          ))}
          {filteredTags.length === 0 && (
            <div className="col-span-full text-center py-12 text-slate-400">
              No tags found.
            </div>
          )}
        </div>
      ) : (
        <Card>
          <CardContent className="p-0">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b bg-slate-50">
                  <th className="text-left p-3 font-medium text-slate-600">Term</th>
                  <th className="text-left p-3 font-medium text-slate-600 hidden md:table-cell">Category</th>
                  <th className="text-left p-3 font-medium text-slate-600">Status</th>
                  <th className="text-left p-3 font-medium text-slate-600 hidden lg:table-cell">Definition</th>
                </tr>
              </thead>
              <tbody>
                {filteredTerms.map((term) => (
                  <tr key={term.id} className="border-b hover:bg-slate-50 cursor-pointer">
                    <td className="p-3">
                      <div className="font-medium text-slate-900">{term.name}</div>
                      <div className="text-xs text-slate-400 font-mono">{term.qualifiedName}</div>
                    </td>
                    <td className="p-3 hidden md:table-cell text-slate-600">{term.category || '—'}</td>
                    <td className="p-3">
                      <Badge className={statusColors[term.status] || ''}>{term.status}</Badge>
                    </td>
                    <td className="p-3 hidden lg:table-cell text-slate-500 line-clamp-1 max-w-xs">
                      {term.definition || term.description || '—'}
                    </td>
                  </tr>
                ))}
                {filteredTerms.length === 0 && (
                  <tr>
                    <td colSpan={4} className="text-center py-8 text-slate-400">
                      No glossary terms found.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </CardContent>
        </Card>
      )}
    </div>
  )
}
