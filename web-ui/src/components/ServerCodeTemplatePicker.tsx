import { useState, type ReactNode } from 'react';
import { useQuery } from '@tanstack/react-query';
import { api } from '../api/client';
import type { ServerCodeTemplateItem } from '../types/api';

interface Props {
  onSelect: (code: string) => void;
  children: (open: () => void) => ReactNode;
}

export function ServerCodeTemplatePicker({ onSelect, children }: Props) {
  const [open, setOpen] = useState(false);
  const [selectedTemplateId, setSelectedTemplateId] = useState<string | null>(null);

  const { data: templates, isLoading } = useQuery({
    queryKey: ['server-code-templates'],
    queryFn: () => api.get<ServerCodeTemplateItem[]>('/api/admin/modules/server-code-templates'),
    enabled: open,
  });

  const selectedTemplate = templates?.find((t) => t.id === selectedTemplateId) ?? null;

  const close = () => {
    setOpen(false);
    setSelectedTemplateId(null);
  };

  const handleUseTemplate = () => {
    if (!selectedTemplate) return;
    onSelect(selectedTemplate.code);
    close();
  };

  return (
    <>
      {children(() => setOpen(true))}
      {open && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
          <div className="flex h-[80vh] w-full max-w-4xl overflow-hidden rounded-lg bg-white shadow-lg">
            <div className="flex w-full flex-col">
              <div className="flex items-center justify-between border-b border-gray-200 p-4">
                <h3 className="text-lg font-semibold text-gray-900">Server Code Templates</h3>
                <button onClick={close} className="text-gray-500 hover:text-gray-700">
                  X
                </button>
              </div>
              <div className="flex flex-1 overflow-hidden">
                <div className="w-1/3 overflow-y-auto border-r border-gray-200">
                  {isLoading && <p className="p-4 text-sm text-gray-500">Loading templates…</p>}
                  {templates?.length === 0 && <p className="p-4 text-sm text-gray-500">No templates available.</p>}
                  {templates?.map((template) => (
                    <button
                      key={template.id}
                      onClick={() => setSelectedTemplateId(template.id)}
                      className={`block w-full border-b border-gray-100 p-3 text-left text-sm hover:bg-gray-50 ${
                        selectedTemplateId === template.id ? 'bg-blue-50' : ''
                      }`}
                    >
                      <div className="font-medium text-gray-900">{template.name}</div>
                      <div className="mt-1 text-xs text-gray-500">{template.description}</div>
                    </button>
                  ))}
                </div>
                <div className="flex w-2/3 flex-col overflow-y-auto p-4">
                  {!selectedTemplate && (
                    <p className="text-sm text-gray-500">Select a template to preview its code.</p>
                  )}
                  {selectedTemplate && (
                    <>
                      <pre className="mb-3 max-h-72 overflow-auto rounded bg-gray-900 p-3 text-xs text-gray-100">
                        <code>{selectedTemplate.code}</code>
                      </pre>
                      <div className="mb-3 rounded bg-amber-50 p-3 text-xs text-amber-800">
                        <p className="mb-1 font-medium">Setup guide</p>
                        <p>{selectedTemplate.setup_guide}</p>
                      </div>
                      <button
                        onClick={handleUseTemplate}
                        className="self-start rounded bg-blue-600 px-4 py-2 text-sm text-white hover:bg-blue-700"
                      >
                        Use this template
                      </button>
                    </>
                  )}
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
