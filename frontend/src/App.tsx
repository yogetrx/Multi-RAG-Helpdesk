
import { useState } from 'react'
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

const knowledgeBases: {
  id: KnowledgeBase
  name: string
  description: string
  icon: string
}[] = [
  {
    id: 'troubleshooting',
    name: 'Troubleshooting',
    description: 'Technical issues and fixes',
    icon: '⚙',
  },
  {
    id: 'access_policies',
    name: 'Access Policies',
    description: 'Permissions and access',
    icon: '🔐',
  },
  {
    id: 'it_documentation',
    name: 'IT Documentation',
    description: 'Internal IT knowledge',
    icon: '📚',
  },
]

function App() {
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
      {
        id: messageId,
        question: trimmedQuestion,
      },
    ])

    setQuestion('')
    setIsLoading(true)

    try {
      const apiResponse = await fetch('/api/ask', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          question: trimmedQuestion,
          top_k: 3,
        }),
      })

      if (!apiResponse.ok) {
        const errorBody = await apiResponse.json().catch(() => null)

        throw new Error(
          errorBody?.detail ||
            `Request failed with status ${apiResponse.status}`,
        )
      }

      const data: AskResponse = await apiResponse.json()

      setMessages((previous) =>
        previous.map((message) =>
          message.id === messageId
            ? { ...message, response: data }
            : message,
        ),
      )
    } catch (error) {
      const errorMessage =
        error instanceof Error
          ? error.message
          : 'Something went wrong. Please try again.'

      setMessages((previous) =>
        previous.map((message) =>
          message.id === messageId
            ? { ...message, error: errorMessage }
            : message,
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

  return (
    <div className="app-container">
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-icon">✦</div>
          <div>
            <h2>Multi-RAG</h2>
            <span>HELPDESK AI</span>
          </div>
        </div>

        <button
          className="new-chat-button"
          onClick={startNewConversation}
        >
          <span>＋</span> New conversation
        </button>

        <div className="sidebar-section">
          <p className="section-label">KNOWLEDGE BASES</p>

          {knowledgeBases.map((kb) => (
            <button
              key={kb.id}
              className={`kb-item ${selectedKB === kb.id ? 'active' : ''}`}
              onClick={() => setSelectedKB(kb.id)}
            >
              <span className="kb-icon">{kb.icon}</span>

              <span className="kb-details">
                <strong>{kb.name}</strong>
                <small>{kb.description}</small>
              </span>

              {selectedKB === kb.id && (
                <span className="active-dot" />
              )}
            </button>
          ))}
        </div>

        <div className="sidebar-bottom">
          <div className="system-status">
            <span className="status-dot" />
            <div>
              <strong>Azure backend</strong>
              <small>Connection configured</small>
            </div>
          </div>

          <div className="profile">
            <div className="avatar">MR</div>
            <div>
              <strong>Helpdesk User</strong>
              <small>AI Support Workspace</small>
            </div>
          </div>
        </div>
      </aside>

      <main className="main-content">
        <header className="topbar">
          <div>
            <span className="breadcrumb">Workspace / </span>
            <strong>{selectedKnowledgeBase.name}</strong>
          </div>

          <div className="topbar-right">
            <span className="environment-badge">
              ● Development
            </span>
            <div className="topbar-avatar">MR</div>
          </div>
        </header>

        <section className="chat-area">
          {messages.length === 0 ? (
            <div className="welcome-screen">
              <div className="welcome-icon">✦</div>

              <span className="eyebrow">
                AI-POWERED IT SUPPORT
              </span>

              <h1>
                How can I help
                <br />
                <span>you today?</span>
              </h1>

              <p className="welcome-description">
                Ask a technical question and let Multi-RAG retrieve
                relevant information from your knowledge bases.
              </p>

              <div className="selected-kb-card">
                <div className="selected-kb-icon">
                  {selectedKnowledgeBase.icon}
                </div>

                <div>
                  <small>KNOWLEDGE BASE NAVIGATION</small>
                  <strong>{selectedKnowledgeBase.name}</strong>
                  <span>{selectedKnowledgeBase.description}</span>
                </div>

                <span className="status-dot" />
              </div>

              <div className="suggestion-heading">
                <span>TRY ASKING</span>
                <span>Suggested questions</span>
              </div>

              <div className="suggestions">
                {[
                  'How do I fix VPN error 809?',
                  'How can I request system access?',
                  'Where can I find IT documentation?',
                ].map((suggestion) => (
                  <button
                    key={suggestion}
                    onClick={() => setQuestion(suggestion)}
                  >
                    {suggestion}
                    <span>↗</span>
                  </button>
                ))}
              </div>
            </div>
          ) : (
            <div className="conversation">
              <div className="conversation-heading">
                <span className="eyebrow">CONVERSATION</span>
                <h2>Ask your AI helpdesk</h2>
              </div>

              {messages.map((message) => (
                <div key={message.id}>
                  <div className="message user">
                    <div className="message-avatar">U</div>
                    <div className="message-body">
                      <strong>You</strong>
                      <p>{message.question}</p>
                    </div>
                  </div>

                  {message.response && (
                    <div className="message assistant">
                      <div className="message-avatar">✦</div>

                      <div className="message-body">
                        <strong>Multi-RAG AI</strong>

                        <p>{message.response.answer}</p>

                        <div className="response-metadata">
                          <span>
                            {message.response.grounded
                              ? '✓ Grounded'
                              : '⚠ Not grounded'}
                          </span>

                          {message.response.selected_knowledge_bases.map(
                            (kb) => (
                              <span key={kb}>{kb}</span>
                            ),
                          )}
                        </div>

                        {message.response.citations.length > 0 && (
                          <div className="citation-panel">
                            <strong>Sources</strong>

                            {message.response.citations.map(
                              (citation) => (
                                <div
                                  className="citation-item"
                                  key={citation.id}
                                >
                                  <span>[{citation.id}]</span>
                                  <div>
                                    <strong>{citation.source}</strong>
                                    <small>
                                      {citation.knowledge_base}
                                    </small>
                                  </div>
                                </div>
                              ),
                            )}
                          </div>
                        )}

                        {message.response.token_usage && (
                          <div className="token-info">
                            Token usage:{' '}
                            {message.response.token_usage.total_tokens ??
                              'Unavailable'}
                          </div>
                        )}
                      </div>
                    </div>
                  )}

                  {message.error && (
                    <div className="integration-notice">
                      <strong>Request failed</strong>
                      <p>{message.error}</p>
                    </div>
                  )}
                </div>
              ))}

              {isLoading && (
                <div className="message assistant">
                  <div className="message-avatar">✦</div>
                  <div className="message-body">
                    <strong>Multi-RAG AI</strong>
                    <p>Searching knowledge bases and generating an answer...</p>
                  </div>
                </div>
              )}
            </div>
          )}
        </section>

        <footer className="composer-area">
          <form className="composer" onSubmit={handleSubmit}>
            <textarea
              value={question}
              onChange={(event) => setQuestion(event.target.value)}
              placeholder="Ask anything about your IT issue..."
              rows={2}
              disabled={isLoading}
              onKeyDown={(event) => {
                if (event.key === 'Enter' && !event.shiftKey) {
                  event.preventDefault()
                  event.currentTarget.form?.requestSubmit()
                }
              }}
            />

            <div className="composer-bottom">
              <span>
                ✦ Multi-RAG automatic routing
              </span>

              <button
                type="submit"
                disabled={!question.trim() || isLoading}
              >
                {isLoading ? 'Thinking...' : 'Send'}
                <span>↑</span>
              </button>
            </div>
          </form>

          <p className="disclaimer">
            AI-generated responses may require verification.
            Do not share passwords or confidential credentials.
          </p>
        </footer>
      </main>
    </div>
  )
}

export default App
