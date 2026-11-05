import { useEffect, useState } from 'react'
import type { FormEvent } from 'react'
import './App.css'

type KnowledgeBase =
  | 'troubleshooting'
  | 'access_policies'
  | 'it_documentation'

type Citation = {
  id: number
  source: string
  knowledge_base: string
}

type AskResponse = {
  question: string
  selected_knowledge_bases: string[]
  answer: string
  citations: Citation[]
  grounded: boolean
  token_usage: {
    input_tokens?: number
    output_tokens?: number
    total_tokens?: number
  } | null
}

type Message = {
  id: number
  question: string
  response?: AskResponse
  error?: string
}

const API_URL = import.meta.env.DEV
  ? '/api/ask'
  : 'https://func-multirag-helpdesk.azurewebsites.net/api/ask'

const HEALTH_URL = import.meta.env.DEV
  ? '/api/health'
  : 'https://func-multirag-helpdesk.azurewebsites.net/api/health'

const knowledgeBases: {
  id: KnowledgeBase
  name: string
  description: string
  icon: string
  detail: string
}[] = [
  {
    id: 'troubleshooting',
    name: 'Troubleshooting',
    description: 'Technical issues and fixes',
    icon: '⌘',
    detail: 'Resolve common IT incidents and technical errors.',
  },
  {
    id: 'access_policies',
    name: 'Access Policies',
    description: 'Permissions and access',
    icon: '◇',
    detail: 'Find guidance for accounts, roles and permissions.',
  },
  {
    id: 'it_documentation',
    name: 'IT Documentation',
    description: 'Internal IT knowledge',
    icon: '▤',
    detail: 'Search internal procedures and technical documentation.',
  },
]

const suggestions = [
  'How do I fix VPN error 809?',
  'How can I request system access?',
  'Where can I find IT documentation?',
]

function App() {
  const [backendStatus, setBackendStatus] = useState<
    'checking' | 'connected' | 'unavailable'
  >('checking')

  useEffect(() => {
    let active = true

    const checkBackend = async () => {
      try {
        const response = await fetch(HEALTH_URL, {
          cache: 'no-store',
        })

        if (!response.ok) {
          throw new Error('Backend unavailable')
        }

        const data: { status?: string } = await response.json()

        if (active) {
          setBackendStatus(data.status === 'ok' ? 'connected' : 'unavailable')
        }
      } catch {
        if (active) {
          setBackendStatus('unavailable')
        }
      }
    }

    void checkBackend()
    const intervalId = window.setInterval(() => {
      void checkBackend()
    }, 30000)

    return () => {
      active = false
      window.clearInterval(intervalId)
    }
  }, [])
  const [selectedKB, setSelectedKB] =
    useState<KnowledgeBase>('troubleshooting')
  const [question, setQuestion] = useState('')
  const [messages, setMessages] = useState<Message[]>([])
  const [isLoading, setIsLoading] = useState(false)

  const selectedKnowledgeBase = knowledgeBases.find(
    (kb) => kb.id === selectedKB,
  )!

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const trimmedQuestion = question.trim()
    if (!trimmedQuestion || isLoading) return

    const messageId = Date.now()
    setMessages((previous) => [
      ...previous,
      { id: messageId, question: trimmedQuestion },
    ])
    setQuestion('')
    setIsLoading(true)

    try {
      const apiResponse = await fetch(API_URL, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question: trimmedQuestion, top_k: 3 }),
      })

      if (!apiResponse.ok) {
        const errorBody = await apiResponse.json().catch(() => null)
        let errorMessage =
          errorBody?.detail ||
          `Request failed with status ${apiResponse.status}`

        if (apiResponse.status === 401) {
          errorMessage = 'Authentication failed. Please contact support.'
        } else if (apiResponse.status === 429) {
          errorMessage = 'Rate limit exceeded. Please wait before trying again.'
        } else if (apiResponse.status >= 500) {
          errorMessage = 'Backend server error. Please try again later.'
        }
        throw new Error(errorMessage)
      }

      const data: AskResponse = await apiResponse.json()
      setMessages((previous) =>
        previous.map((message) =>
          message.id === messageId ? { ...message, response: data } : message,
        ),
      )
    } catch (error) {
      const errorMessage =
        error instanceof Error
          ? error.message
          : 'Something went wrong. Please try again.'
      setMessages((previous) =>
        previous.map((message) =>
          message.id === messageId ? { ...message, error: errorMessage } : message,
        ),
      )
    } finally {
      setIsLoading(false)
    }
  }

  function startNewConversation() {
    setMessages([])
    setQuestion('')
  }

  function useSuggestion(value: string) {
    setQuestion(value)
  }

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-mark">✳</div>
          <div className="brand-copy">
            <strong>Multi-RAG</strong>
            <span>HELPDESK AI</span>
          </div>
        </div>

        <button className="new-chat-button" onClick={startNewConversation}>
          <span>＋</span> New conversation
        </button>

        <div className="sidebar-label">WORKSPACE</div>
        <button className="nav-item active">
          <span className="nav-icon">▦</span>
          <span>AI Assistant</span>
          <span className="nav-current" />
        </button>

        <div className="sidebar-label knowledge-label">KNOWLEDGE BASES</div>
        <div className="sidebar-kbs">
          {knowledgeBases.map((kb) => (
            <button
              key={kb.id}
              className={`kb-nav-item ${selectedKB === kb.id ? 'selected' : ''}`}
              onClick={() => setSelectedKB(kb.id)}
            >
              <span className="kb-nav-icon">{kb.icon}</span>
              <span className="kb-nav-copy">
                <strong>{kb.name}</strong>
                <small>{kb.description}</small>
              </span>
              {selectedKB === kb.id && <span className="kb-selected-dot" />}
            </button>
          ))}
        </div>

        <div className="sidebar-spacer" />

        <div className="sidebar-system-card">
          <div className="system-card-top">
            <span
              className={`online-indicator ${
                backendStatus === 'connected'
                  ? 'status-connected'
                  : backendStatus === 'unavailable'
                    ? 'status-unavailable'
                    : 'status-checking'
              }`}
            />
            <span>
              {backendStatus === 'connected'
                ? 'Connected service'
                : backendStatus === 'unavailable'
                  ? 'Service unavailable'
                  : 'Checking service'}
            </span>
            <span className="system-live">
              {backendStatus === 'connected'
                ? 'LIVE'
                : backendStatus === 'unavailable'
                  ? 'OFFLINE'
                  : 'CHECKING'}
            </span>
          </div>
          <strong>Azure backend</strong>
          <small>Requests routed through secure API proxy</small>
        </div>

        <div className="profile-row">
          <div className="profile-avatar">HD</div>
          <div>
            <strong>Helpdesk User</strong>
            <small>Support workspace</small>
          </div>
          <span className="profile-menu">···</span>
        </div>
      </aside>

      <main className="main-panel">
        <header className="topbar">
          <div className="breadcrumbs">
            <span>Workspace</span><span className="crumb-slash">/</span>
            <strong>AI Assistant</strong>
          </div>
          <div className="topbar-actions">
            <div className="secure-label"><span>⌑</span> Secure workspace</div>
            <div className="environment-pill"><span /> Azure Demo</div>
            <div className="topbar-avatar">HD</div>
          </div>
        </header>

        <div className="page-content">
          <section className="page-intro">
            <div>
              <div className="eyebrow"><span className="eyebrow-line" /> INTELLIGENT IT SUPPORT</div>
              <h1>Your IT knowledge,<br /><span>one conversation away.</span></h1>
              <p>Ask questions in natural language. Multi-RAG finds relevant knowledge and returns answers with source references.</p>
            </div>
            <div className="intro-orbit" aria-hidden="true">
              <div className="orbit-ring ring-one" />
              <div className="orbit-ring ring-two" />
              <div className="orbit-core">✳</div>
              <span className="orbit-dot dot-one" />
              <span className="orbit-dot dot-two" />
              <span className="orbit-dot dot-three" />
            </div>
          </section>

          <section className="overview-grid" aria-label="System overview">
            <div className="overview-card">
              <div className="overview-icon violet">▤</div>
              <div><span>Knowledge bases</span><strong>03</strong><small>Connected collections</small></div>
              <span className="card-corner">↗</span>
            </div>
            <div className="overview-card">
              <div className="overview-icon blue">⌕</div>
              <div><span>Retrieval engine</span><strong>FAISS</strong><small>Vector similarity search</small></div>
              <span className="card-corner">↗</span>
            </div>
            <div className="overview-card">
              <div className="overview-icon green">✧</div>
              <div><span>Answer generation</span><strong>Azure OpenAI</strong><small>Grounded response generation</small></div>
              <span className="card-corner">↗</span>
            </div>
            <div className="overview-card">
              <div className="overview-icon amber">⌁</div>
              <div><span>Sources per answer</span><strong>Top 3</strong><small>Configurable retrieval count</small></div>
              <span className="card-corner">↗</span>
            </div>
          </section>

          <section className="workspace-grid">
            <div className="chat-column">
              <div className="section-heading">
                <div>
                  <span className="section-kicker">YOUR WORKSPACE</span>
                  <h2>AI helpdesk assistant</h2>
                </div>
                {messages.length > 0 && (
                  <button className="text-button" onClick={startNewConversation}>＋ New chat</button>
                )}
              </div>

              <div className={`chat-card ${messages.length === 0 ? 'empty-chat' : ''}`}>
                {messages.length === 0 ? (
                  <div className="empty-state">
                    <div className="assistant-emblem"><span>✳</span></div>
                    <span className="empty-kicker">READY WHEN YOU ARE</span>
                    <h3>What can I help you<br /><span>figure out today?</span></h3>
                    <p>Describe an IT issue or ask about a process. I'll search the connected knowledge bases and show the sources behind my answer.</p>

                    <div className="active-knowledge">
                      <div className="active-knowledge-icon">{selectedKnowledgeBase.icon}</div>
                      <div className="active-knowledge-copy">
                        <small>SELECTED KNOWLEDGE AREA</small>
                        <strong>{selectedKnowledgeBase.name}</strong>
                        <span>{selectedKnowledgeBase.description}</span>
                      </div>
                      <span className="active-check">✓</span>
                    </div>

                    <div className="suggestion-title"><span>QUICK START</span><span>Choose a question</span></div>
                    <div className="suggestion-list">
                      {suggestions.map((suggestion) => (
                        <button key={suggestion} onClick={() => useSuggestion(suggestion)}>
                          <span>{suggestion}</span><span className="suggestion-arrow">↗</span>
                        </button>
                      ))}
                    </div>
                  </div>
                ) : (
                  <div className="conversation">
                    <div className="conversation-topline">
                      <span className="conversation-live"><span /> CONVERSATION ACTIVE</span>
                      <span>{messages.length} {messages.length === 1 ? 'question' : 'questions'}</span>
                    </div>
                    {messages.map((message) => (
                      <div className="message-group" key={message.id}>
                        <div className="message user-message">
                          <div className="message-avatar user-avatar">YOU</div>
                          <div className="message-content">
                            <div className="message-meta"><strong>You</strong><span>Question</span></div>
                            <p>{message.question}</p>
                          </div>
                        </div>

                        {message.response && (
                          <div className="message assistant-message">
                            <div className="message-avatar assistant-avatar">✳</div>
                            <div className="message-content">
                              <div className="message-meta"><strong>Multi-RAG AI</strong><span>Answer</span></div>
                              <p className="answer-text">{message.response.answer}</p>
                              <div className="response-badges">
                                <span className={message.response.grounded ? 'grounded-badge' : 'ungrounded-badge'}>
                                  {message.response.grounded ? '✓ Grounded response' : '⚠ Grounding not confirmed'}
                                </span>
                                {message.response.selected_knowledge_bases.map((kb) => <span className="kb-badge" key={kb}>{kb}</span>)}
                              </div>
                              {message.response.citations.length > 0 && (
                                <div className="sources-panel">
                                  <div className="sources-heading"><strong>Sources used</strong><span>{message.response.citations.length} references</span></div>
                                  <div className="source-list">
                                    {message.response.citations.map((citation) => (
                                      <div className="source-row" key={citation.id}>
                                        <span className="source-number">[{citation.id}]</span>
                                        <div><strong>{citation.source}</strong><small>{citation.knowledge_base}</small></div>
                                        <span className="source-arrow">↗</span>
                                      </div>
                                    ))}
                                  </div>
                                </div>
                              )}
                              {message.response.token_usage && (
                                <div className="token-footer">
                                  <span>◈ Token usage</span>
                                  <strong>{message.response.token_usage.total_tokens ?? 'Unavailable'}</strong>
                                  <span>total tokens</span>
                                </div>
                              )}
                            </div>
                          </div>
                        )}

                        {message.error && <div className="error-panel"><strong>Request failed</strong><p>{message.error}</p></div>}
                      </div>
                    ))}
                    {isLoading && (
                      <div className="message assistant-message loading-message">
                        <div className="message-avatar assistant-avatar">✳</div>
                        <div className="message-content">
                          <div className="message-meta"><strong>Multi-RAG AI</strong><span>Working</span></div>
                          <p>Searching knowledge and preparing your answer<span className="typing-dots"><i /><i /><i /></span></p>
                        </div>
                      </div>
                    )}
                  </div>
                )}
              </div>

              <form className="composer" onSubmit={handleSubmit}>
                <textarea
                  value={question}
                  onChange={(event) => setQuestion(event.target.value)}
                  placeholder="Ask a question about your IT issue..."
                  rows={2}
                  disabled={isLoading}
                  onKeyDown={(event) => {
                    if (event.key === 'Enter' && !event.shiftKey) {
                      event.preventDefault()
                      event.currentTarget.form?.requestSubmit()
                    }
                  }}
                />
                <div className="composer-footer">
                  <div className="composer-hint"><span>✳</span> Multi-RAG automatic routing <i /> Sources included with answers</div>
                  <button type="submit" disabled={!question.trim() || isLoading}>
                    {isLoading ? 'Thinking' : 'Send question'} <span>↑</span>
                  </button>
                </div>
              </form>
              <p className="disclaimer">AI-generated responses may require verification. Never share passwords or confidential credentials.</p>
            </div>

            <aside className="info-column">
              <div className="side-panel">
                <div className="panel-heading"><div><span className="section-kicker">CONNECTED CONTENT</span><h3>Knowledge bases</h3></div><span className="panel-count">03</span></div>
                <p className="panel-description">Choose an area to guide your question. The backend can automatically route queries across relevant knowledge bases.</p>
                <div className="knowledge-card-list">
                  {knowledgeBases.map((kb, index) => (
                    <button key={kb.id} className={`knowledge-card ${selectedKB === kb.id ? 'chosen' : ''}`} onClick={() => setSelectedKB(kb.id)}>
                      <span className={`knowledge-card-icon kb-color-${index}`}>{kb.icon}</span>
                      <span className="knowledge-card-copy"><strong>{kb.name}</strong><small>{kb.detail}</small></span>
                      <span className="knowledge-card-check">{selectedKB === kb.id ? '✓' : '＋'}</span>
                    </button>
                  ))}
                </div>
                <div className="panel-footnote"><span className="online-indicator" /> 3 knowledge areas configured</div>
              </div>

              <div className="side-panel capability-panel">
                <div className="panel-heading"><div><span className="section-kicker">UNDER THE HOOD</span><h3>How it works</h3></div><span className="capability-spark">✧</span></div>
                <div className="capability-list">
                  <div><span className="capability-number">01</span><div><strong>Query understanding</strong><small>Interprets the user's IT question</small></div></div>
                  <div><span className="capability-number">02</span><div><strong>Knowledge retrieval</strong><small>Finds relevant content with FAISS</small></div></div>
                  <div><span className="capability-number">03</span><div><strong>Grounded generation</strong><small>Uses retrieved context to form an answer</small></div></div>
                  <div><span className="capability-number">04</span><div><strong>Source references</strong><small>Returns citations with the response</small></div></div>
                </div>
              </div>

              <div className="privacy-note"><span>♧</span><div><strong>Designed for responsible support</strong><small>Responses include source references. Verify critical instructions before taking action.</small></div></div>
            </aside>
          </section>
          <footer className="page-footer"><span>Multi-RAG Helpdesk</span><span>AI-powered knowledge assistance <i /> Built for reliable IT support</span></footer>
        </div>
      </main>
    </div>
  )
}

export default App
