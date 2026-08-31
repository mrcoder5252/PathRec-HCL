'use client'

import React, { useState, useEffect } from 'react'
import {
  Bell, BookOpen, BriefcaseBusiness, CheckCircle2, ChevronDown, ChevronRight,
  CircleHelp, ClipboardCheck, ExternalLink, FileText, FolderKanban, GraduationCap,
  LayoutDashboard, LineChart, LogIn, LogOut, Menu, MessageSquare, MoreHorizontal,
  Play, Plus, RefreshCw, RotateCcw, Search, Settings, Sparkles, Target, UserCheck, X
} from 'lucide-react'

import {
  User, getCurrentUser, loginUser, registerUser, removeToken, setToken,
  startQuiz, submitQuizAnswer, getRoadmap, submitFeedback, compareGoals,
  sendCopilotMessage, QuizQuestion, Milestone, CompareResponse
} from '@/lib/api'

const nav = [
  ['Dashboard', LayoutDashboard],
  ['Career Assessment', ClipboardCheck],
  ['Learning Roadmap', BookOpen],
  ['Why Not X? Comparison', Sparkles],
  ['Skills Map', LineChart],
  ['Projects', FolderKanban],
  ['Resume', FileText],
  ['Interview Prep', MessageSquare]
] as const

export default function Page() {
  const [active, setActive] = useState<string>('Dashboard')
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [user, setUser] = useState<User | null>(null)
  const [showAuthModal, setShowAuthModal] = useState(false)
  const [authTab, setAuthTab] = useState<'login' | 'register'>('login')
  const [authLoading, setAuthLoading] = useState(false)
  const [authError, setAuthError] = useState('')

  // Auth Form State
  const [email, setEmail] = useState('alex@example.com')
  const [password, setPassword] = useState('password123')
  const [name, setName] = useState('Alex Morgan')
  const [targetRole, setTargetRole] = useState('Backend Developer')

  // Load User on Mount
  useEffect(() => {
    async function load() {
      const u = await getCurrentUser()
      if (u) {
        setUser(u)
      } else {
        // Auto default to demo profile
        setUser({
          id: 'user_alex_001',
          email: 'alex@example.com',
          name: 'Alex Morgan',
          target_role: 'Backend Developer',
          domain: 'backend',
          goal_skill: 'deployment',
          confidence: { py_basics: 0.8, sql_basics: 0.6, rest_apis: 0.5 },
          known_skills: ['py_basics', 'sql_basics', 'rest_apis']
        })
      }
    }
    load()
  }, [])

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault()
    setAuthLoading(true)
    setAuthError('')
    try {
      const res = await loginUser({ email, password })
      setToken(res.token)
      setUser(res.user)
      setShowAuthModal(false)
    } catch (err: any) {
      setAuthError(err.message || 'Login failed')
    } finally {
      setAuthLoading(false)
    }
  }

  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault()
    setAuthLoading(true)
    setAuthError('')
    try {
      const res = await registerUser({ email, password, name, target_role: targetRole, goal_skill: 'deployment' })
      setToken(res.token)
      setUser(res.user)
      setShowAuthModal(false)
    } catch (err: any) {
      setAuthError(err.message || 'Registration failed')
    } finally {
      setAuthLoading(false)
    }
  }

  const handleLogout = () => {
    removeToken()
    setUser(null)
  }

  return (
    <div className="app-shell">
      {/* Sidebar */}
      <aside className={`sidebar ${sidebarOpen ? 'open' : ''}`}>
        <div className="brand">
          <span className="brand-mark"><Sparkles size={16} /></span>
          <b>NEXORA</b>
          <button className="mobile-close" onClick={() => setSidebarOpen(false)}><X size={18} /></button>
        </div>

        {/* User Card */}
        <div className="workspace-switch" onClick={() => setShowAuthModal(true)} style={{ cursor: 'pointer' }}>
          <span className="avatar sm">{user ? user.name.slice(0, 2).toUpperCase() : 'GU'}</span>
          <span>
            <b>{user ? user.name : 'Guest User'}</b>
            <small>{user ? user.target_role : 'Click to Sign In'}</small>
          </span>
          <ChevronDown size={14} />
        </div>

        <p className="side-label">Workspace</p>
        <nav>
          {nav.map(([label, Icon]) => (
            <button
              key={label}
              className={active === label ? 'active' : ''}
              onClick={() => { setActive(label); setSidebarOpen(false) }}
            >
              <Icon size={16} />
              <span>{label}</span>
              {label === 'Career Assessment' && <i className="nav-dot" />}
            </button>
          ))}
        </nav>

        <div className="sidebar-bottom">
          {user ? (
            <button onClick={handleLogout} style={{ color: '#fca5a5' }}><LogOut size={16} /> Sign Out</button>
          ) : (
            <button onClick={() => setShowAuthModal(true)}><LogIn size={16} /> Sign In / Register</button>
          )}
          <div className="upgrade">
            <Sparkles size={18} />
            <div>
              <b>PathRec Engine Active</b>
              <small>Graph + RAG + Staircase AI</small>
            </div>
          </div>
        </div>
      </aside>

      {/* Main Container */}
      <main className="main">
        {/* Topbar */}
        <header className="topbar">
          <button className="mobile-menu" onClick={() => setSidebarOpen(true)}><Menu size={20} /></button>
          <div className="crumb">
            <span>Workspace</span>
            <ChevronRight size={14} />
            <b>{active}</b>
          </div>

          <div className="top-actions">
            {user ? (
              <div className="profile" onClick={() => setShowAuthModal(true)} style={{ cursor: 'pointer' }}>
                <span className="avatar">{user.name.slice(0, 2).toUpperCase()}</span>
                <span className="profile-copy">
                  <b>{user.name}</b>
                  <small>{user.email}</small>
                </span>
                <ChevronDown size={14} />
              </div>
            ) : (
              <button className="primary" onClick={() => setShowAuthModal(true)} style={{ padding: '8px 14px' }}>
                <LogIn size={14} /> Sign In
              </button>
            )}
          </div>
        </header>

        {/* View Switcher */}
        <div className="page-content">
          {active === 'Dashboard' && <DashboardView user={user} onNavigate={setActive} />}
          {active === 'Career Assessment' && <CareerAssessmentQuizView user={user} onNavigate={setActive} />}
          {active === 'Learning Roadmap' && <LearningRoadmapView user={user} />}
          {active === 'Why Not X? Comparison' && <GoalComparisonView user={user} />}
          {active === 'Skills Map' && <SkillsMapView user={user} onNavigate={setActive} />}
          {active === 'Projects' && <ProjectsView />}
          {active === 'Resume' && <ResumeView user={user} />}
          {active === 'Interview Prep' && <InterviewPrepView />}
        </div>

        <footer>
          <span>© 2026 NEXORA · PathRec AI Recommender Engine</span>
          <span>Adaptive Multi-Tier Learning Path</span>
        </footer>
      </main>

      {/* Right AI Copilot */}
      <CareerCopilot user={user} onNavigate={setActive} />

      {/* Auth Modal */}
      {showAuthModal && (
        <div className="modal-overlay" onClick={() => setShowAuthModal(false)}>
          <div className="modal-card" onClick={(e) => e.stopPropagation()}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                <span className="brand-mark" style={{ width: '24px', height: '24px' }}><Sparkles size={13} /></span>
                <h2 style={{ margin: 0, fontSize: '18px' }}>NEXORA Account</h2>
              </div>
              <button onClick={() => setShowAuthModal(false)}><X size={18} /></button>
            </div>

            <div className="modal-tabs">
              <div
                className={`modal-tab ${authTab === 'login' ? 'active' : ''}`}
                onClick={() => { setAuthTab('login'); setAuthError('') }}
              >
                Sign In
              </div>
              <div
                className={`modal-tab ${authTab === 'register' ? 'active' : ''}`}
                onClick={() => { setAuthTab('register'); setAuthError('') }}
              >
                Create Account
              </div>
            </div>

            {authError && (
              <div style={{ background: '#fee2e2', color: '#991b1b', padding: '10px', borderRadius: '8px', fontSize: '12px' }}>
                {authError}
              </div>
            )}

            <form onSubmit={authTab === 'login' ? handleLogin : handleRegister} style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
              {authTab === 'register' && (
                <>
                  <div className="form-group">
                    <label>Full Name</label>
                    <input value={name} onChange={(e) => setName(e.target.value)} required placeholder="Your name" />
                  </div>
                  <div className="form-group">
                    <label>Target Career Role</label>
                    <input value={targetRole} onChange={(e) => setTargetRole(e.target.value)} placeholder="e.g. Backend Developer, Data Engineer" />
                  </div>
                </>
              )}

              <div className="form-group">
                <label>Email Address</label>
                <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} required placeholder="name@example.com" />
              </div>

              <div className="form-group">
                <label>Password</label>
                <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} required placeholder="••••••••" />
              </div>

              <button className="primary" type="submit" disabled={authLoading} style={{ marginTop: '10px', justifyContent: 'center' }}>
                {authLoading ? 'Authenticating...' : authTab === 'login' ? 'Sign In' : 'Create Account'}
              </button>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}

/* =========================================================================
   1. DASHBOARD VIEW
   ========================================================================= */
function DashboardView({ user, onNavigate }: { user: User | null; onNavigate: (v: string) => void }) {
  const readiness = 74
  return (
    <>
      <div className="hero-card">
        <div>
          <p className="eyebrow">Welcome back, {user ? user.name : 'Learner'}</p>
          <h1>Your career roadmap, optimized.</h1>
          <p>PathRec analyzes your skill graph, assesses prerequisites dynamically, and generates adaptive course sequences in real-time.</p>
          <div style={{ display: 'flex', gap: '12px', marginTop: '18px' }}>
            <button className="primary" onClick={() => onNavigate('Career Assessment')}>
              <ClipboardCheck size={16} /> Take Staircase Quiz
            </button>
            <button className="secondary" style={{ margin: 0 }} onClick={() => onNavigate('Learning Roadmap')}>
              <BookOpen size={16} /> View Roadmap
            </button>
          </div>
        </div>
        <div className="readiness">
          <span>Career readiness</span>
          <b>{readiness}%</b>
          <div className="progress mint"><span style={{ width: `${readiness}%` }} /></div>
          <small>+9% adaptive boost</small>
        </div>
      </div>

      <div className="stat-grid">
        {[
          ['Target Goal', user?.goal_skill?.replace('_', ' ').toUpperCase() || 'DEPLOYMENT', 'Goal Skill'],
          ['Skills Mastered', Object.values(user?.confidence || {}).filter((c) => c >= 0.5).length.toString(), 'Confidence >= 50%'],
          ['Adaptive Re-routes', 'Live Active', 'Instant Feedback Loop'],
          ['Curated Courses', '65+', 'RAG + Cosine Match']
        ].map(([a, b, c]) => (
          <div className="stat-card" key={a}>
            <small>{a}</small>
            <strong>{b}</strong>
            <span>{c}</span>
          </div>
        ))}
      </div>

      <div className="dashboard-grid">
        <div className="panel signal-panel">
          <div className="panel-head">
            <div>
              <p className="eyebrow">Skill Graph Signal</p>
              <h2>Current Capability Assessment</h2>
            </div>
            <span className="tag mint-tag">Graph Connected</span>
          </div>
          <div className="signal-score">
            <div className="score-ring">
              <b>78</b>
              <span>signal</span>
            </div>
            <div>
              <h3>Target: {user?.target_role || 'Backend Developer'}</h3>
              <p>Topological graph sorting has identified your prerequisite sequence.</p>
            </div>
          </div>
          <div className="insight-box">
            <Sparkles size={16} />
            <span>Recommended Next Move: Take the <b>Career Assessment Quiz</b> to recalibrate your confidence on backend prerequisites.</span>
          </div>
        </div>

        <div className="panel action-panel">
          <div className="panel-head">
            <div>
              <p className="eyebrow">Quick Actions</p>
              <h2>Focus Modules</h2>
            </div>
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', marginTop: '10px' }}>
            <button className="action-row" onClick={() => onNavigate('Career Assessment')}>
              <span className="check">1</span>
              <span>
                <b>Diagnostic Staircase Quiz</b>
                <small>Adaptive difficulty testing</small>
              </span>
              <ChevronRight size={15} />
            </button>
            <button className="action-row" onClick={() => onNavigate('Learning Roadmap')}>
              <span className="check">2</span>
              <span>
                <b>Adaptive Milestone Roadmap</b>
                <small>View courses & trigger re-routing</small>
              </span>
              <ChevronRight size={15} />
            </button>
            <button className="action-row" onClick={() => onNavigate('Why Not X? Comparison')}>
              <span className="check">3</span>
              <span>
                <b>Compare Alternative Goals</b>
                <small>Why not System Design vs Deployment?</small>
              </span>
              <ChevronRight size={15} />
            </button>
          </div>
        </div>
      </div>
    </>
  )
}

/* =========================================================================
   2. CAREER ASSESSMENT (ADAPTIVE STAIRCASE QUIZ VIEW)
   ========================================================================= */
function CareerAssessmentQuizView({ user, onNavigate }: { user: User | null; onNavigate: (v: string) => void }) {
  const [domain, setDomain] = useState('backend')
  const [quizState, setQuizState] = useState<'idle' | 'active' | 'completed'>('idle')
  const [loading, setLoading] = useState(false)
  const [sessionId, setSessionId] = useState('')
  const [currentQuestion, setCurrentQuestion] = useState<QuizQuestion | null>(null)
  const [questionNum, setQuestionNum] = useState(1)
  const [totalQuestions, setTotalQuestions] = useState(6)
  const [selectedOption, setSelectedOption] = useState<string | null>(null)
  const [evalResult, setEvalResult] = useState<{ is_correct: boolean; correct_answer: string; explanation?: string } | null>(null)
  const [finalSummary, setFinalSummary] = useState<{ confidence: Record<string, number>; correct_count: number; total_answered: number } | null>(null)

  const startNewQuiz = async () => {
    setLoading(true)
    try {
      const res = await startQuiz(domain, 6, user?.id || 'guest')
      setSessionId(res.session_id)
      setCurrentQuestion(res.question)
      setQuestionNum(res.question_number)
      setTotalQuestions(res.total_questions)
      setSelectedOption(null)
      setEvalResult(null)
      setFinalSummary(null)
      setQuizState('active')
    } catch (err) {
      alert('Error starting quiz: ' + err)
    } finally {
      setLoading(false)
    }
  }

  const handleSelect = async (optKey: string) => {
    if (!currentQuestion || selectedOption || loading) return
    setSelectedOption(optKey)
    setLoading(true)
    try {
      const res = await submitQuizAnswer(sessionId, currentQuestion.id, optKey)
      setEvalResult({
        is_correct: res.is_correct,
        correct_answer: res.correct_answer || '',
        explanation: res.explanation
      })

      setTimeout(() => {
        if (res.completed) {
          setFinalSummary({
            confidence: res.confidence || {},
            correct_count: res.correct_count || 0,
            total_answered: res.total_answered || 6
          })
          setQuizState('completed')
        } else if (res.next_question) {
          setCurrentQuestion(res.next_question)
          setQuestionNum(res.question_number || questionNum + 1)
          setSelectedOption(null)
          setEvalResult(null)
        }
        setLoading(false)
      }, 1400)
    } catch (err) {
      alert('Error submitting answer: ' + err)
      setLoading(false)
    }
  }

  return (
    <section className="module">
      <div className="module-title">
        <div>
          <p className="eyebrow">Adaptive Diagnostic Engine</p>
          <h1>Career Assessment (Staircase Quiz)</h1>
          <p className="subtitle">
            Questions dynamically adapt in real-time based on your answers: correct moves you up (Easy → Medium → Hard), while mistakes calibrate downwards.
          </p>
        </div>
      </div>

      {quizState === 'idle' && (
        <div className="quiz-card" style={{ textAlign: 'center', padding: '48px 32px' }}>
          <div style={{ width: '56px', height: '56px', borderRadius: '16px', background: '#ede9fe', color: 'var(--violet)', display: 'grid', placeItems: 'center', margin: '0 auto 18px' }}>
            <ClipboardCheck size={28} />
          </div>
          <h2>Ready for your Diagnostic Evaluation?</h2>
          <p style={{ maxWidth: '520px', margin: '10px auto 24px', color: 'var(--muted)', fontSize: '13px' }}>
            This 6-question staircase assessment measures your baseline confidence across Python, REST APIs, SQL, Auth, and Deployment.
          </p>

          <div style={{ display: 'flex', justifyContent: 'center', gap: '16px', alignItems: 'center', marginBottom: '24px' }}>
            <label style={{ fontSize: '12px', fontWeight: 'bold' }}>Domain:</label>
            <select
              value={domain}
              onChange={(e) => setDomain(e.target.value)}
              style={{ padding: '8px 16px', borderRadius: '8px', border: '1px solid var(--line)', fontSize: '13px' }}
            >
              <option value="backend">Backend Engineering</option>
            </select>
          </div>

          <button className="primary" onClick={startNewQuiz} disabled={loading} style={{ margin: '0 auto', padding: '12px 28px', fontSize: '14px' }}>
            <Play size={16} /> {loading ? 'Starting Quiz...' : 'Begin Adaptive Quiz'}
          </button>
        </div>
      )}

      {quizState === 'active' && currentQuestion && (
        <div className="quiz-card">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '18px' }}>
            <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
              <span style={{ fontSize: '12px', fontWeight: 'bold', color: 'var(--muted)' }}>
                Question {questionNum} of {totalQuestions}
              </span>
              <span className={`quiz-badge ${currentQuestion.difficulty}`}>
                {currentQuestion.difficulty} Tier
              </span>
            </div>
            <span style={{ fontSize: '11px', color: 'var(--muted)', background: '#f1f5f9', padding: '4px 10px', borderRadius: '6px' }}>
              Skill: <b>{currentQuestion.skill_id}</b>
            </span>
          </div>

          <h2 style={{ fontSize: '18px', lineHeight: '1.45', marginBottom: '24px' }}>
            {currentQuestion.question}
          </h2>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
            {Object.entries(currentQuestion.options).map(([optKey, optVal]) => {
              let optClass = 'quiz-option'
              if (selectedOption === optKey) {
                optClass += ' selected'
                if (evalResult) {
                  optClass += evalResult.is_correct ? ' correct' : ' incorrect'
                }
              } else if (evalResult && !evalResult.is_correct && optKey === evalResult.correct_answer) {
                optClass += ' correct'
              }

              return (
                <button
                  key={optKey}
                  className={optClass}
                  onClick={() => handleSelect(optKey)}
                  disabled={loading}
                >
                  <span style={{ width: '28px', height: '28px', borderRadius: '8px', background: '#f0efff', color: 'var(--violet)', display: 'grid', placeItems: 'center', fontWeight: 'bold', fontSize: '12px' }}>
                    {optKey}
                  </span>
                  <span style={{ fontSize: '13px', flex: 1 }}>{optVal}</span>
                </button>
              )
            })}
          </div>

          {evalResult && (
            <div style={{ marginTop: '20px', padding: '14px', borderRadius: '10px', background: evalResult.is_correct ? '#ecfdf5' : '#fef2f2', color: evalResult.is_correct ? '#065f46' : '#991b1b', fontSize: '13px' }}>
              <b>{evalResult.is_correct ? '✓ Excellent! Correct answer.' : '✗ Incorrect answer.'}</b>
              {evalResult.explanation && <p style={{ margin: '4px 0 0' }}>{evalResult.explanation}</p>}
            </div>
          )}
        </div>
      )}

      {quizState === 'completed' && finalSummary && (
        <div className="quiz-card">
          <div style={{ textAlign: 'center', marginBottom: '28px' }}>
            <span style={{ fontSize: '36px' }}>🎉</span>
            <h2 style={{ fontSize: '24px', marginTop: '10px' }}>Assessment Completed!</h2>
            <p style={{ color: 'var(--muted)', fontSize: '13px' }}>
              You answered <b>{finalSummary.correct_count}</b> out of <b>{finalSummary.total_answered}</b> questions correctly.
            </p>
          </div>

          <h3 style={{ fontSize: '15px', marginBottom: '14px' }}>Calculated Skill Confidence Profile:</h3>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '14px', marginBottom: '28px' }}>
            {Object.entries(finalSummary.confidence).map(([sid, conf]) => (
              <div key={sid} style={{ background: '#f8fafc', border: '1px solid var(--line)', padding: '14px 16px', borderRadius: '12px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '12px', marginBottom: '6px' }}>
                  <b>{sid}</b>
                  <strong style={{ color: conf >= 0.5 ? 'var(--mint)' : 'var(--orange)' }}>{Math.round(conf * 100)}%</strong>
                </div>
                <div className="progress" style={{ height: '6px' }}>
                  <span style={{ width: `${conf * 100}%`, background: conf >= 0.5 ? 'var(--mint)' : 'var(--orange)' }} />
                </div>
              </div>
            ))}
          </div>

          <div style={{ display: 'flex', justifyContent: 'center', gap: '16px' }}>
            <button className="secondary" onClick={startNewQuiz}>
              <RotateCcw size={15} /> Retake Assessment
            </button>
            <button className="primary" onClick={() => onNavigate('Learning Roadmap')}>
              <Sparkles size={16} /> Generate Personalized Roadmap
            </button>
          </div>
        </div>
      )}
    </section>
  )
}

/* =========================================================================
   3. ADAPTIVE LEARNING ROADMAP VIEW (WITH LIVE RE-ROUTING)
   ========================================================================= */
function LearningRoadmapView({ user }: { user: User | null }) {
  const [goalSkill, setGoalSkill] = useState(user?.goal_skill || 'deployment')
  const [roadmap, setRoadmap] = useState<Milestone[]>([])
  const [narration, setNarration] = useState('')
  const [loading, setLoading] = useState(false)
  const [rerouteAlert, setRerouteAlert] = useState<string | null>(null)
  const [confidence, setConfidence] = useState<Record<string, number>>(user?.confidence || { py_basics: 0.8, sql_basics: 0.6 })

  const fetchCurrentRoadmap = async (goal: string) => {
    setLoading(true)
    try {
      const known = Object.entries(confidence)
        .filter(([_, c]) => c >= 0.5)
        .map(([s]) => s)

      const res = await getRoadmap(known, goal)
      setRoadmap(res.milestones)
      setNarration(res.narration || '')
    } catch (err: any) {
      alert('Error fetching roadmap: ' + err.message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchCurrentRoadmap(goalSkill)
  }, [goalSkill])

  // Trigger feedback event (Completion, Test Failure, Skip)
  const handleFeedback = async (skillId: string, eventType: 'completion' | 'quiz_score' | 'skip', score?: number) => {
    try {
      const res = await submitFeedback(user?.id || 'guest', skillId, eventType, score)
      setConfidence(res.updated_confidence)
      setRoadmap(res.re_routed_roadmap.milestones)

      let actionDesc = ''
      if (eventType === 'completion') actionDesc = `Completed '${skillId}' (+confidence)`
      if (eventType === 'quiz_score') actionDesc = `Quiz score on '${skillId}' recorded (${score})`
      if (eventType === 'skip') actionDesc = `Skipped '${skillId}' (-confidence)`

      setRerouteAlert(`⚡ Adaptive Re-Route Triggered: ${actionDesc}. Roadmap updated to ${res.re_routed_roadmap.total_milestones} milestones.`)
      setTimeout(() => setRerouteAlert(null), 6000)
    } catch (err: any) {
      alert('Feedback submission error: ' + err.message)
    }
  }

  return (
    <section className="module">
      <div className="module-title">
        <div>
          <p className="eyebrow">Dynamic Sequence Generator</p>
          <h1>Adaptive Learning Roadmap</h1>
          <p className="subtitle">
            Prerequisites are topologically sorted using NetworkX. Every milestone attaches real courses via TF-IDF cosine retrieval. Completing or failing modules automatically re-routes your path.
          </p>
        </div>

        <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
          <label style={{ fontSize: '12px', fontWeight: 'bold' }}>Goal Skill:</label>
          <select
            value={goalSkill}
            onChange={(e) => setGoalSkill(e.target.value)}
            style={{ padding: '8px 16px', borderRadius: '8px', border: '1px solid var(--line)', fontSize: '13px' }}
          >
            <option value="deployment">Deployment (DevOps & Hosting)</option>
            <option value="system_design_basics">System Design Basics</option>
            <option value="rest_apis">REST API Design</option>
            <option value="auth">Authentication & JWT</option>
            <option value="sqlalchemy">SQLAlchemy & ORM</option>
          </select>
          <button className="secondary" onClick={() => fetchCurrentRoadmap(goalSkill)} style={{ margin: 0 }}>
            <RefreshCw size={14} /> Refresh
          </button>
        </div>
      </div>

      {rerouteAlert && (
        <div className="reroute-banner">
          <Sparkles size={20} color="var(--violet)" />
          <span style={{ fontSize: '13px', color: '#1e1b4b', fontWeight: 'bold' }}>{rerouteAlert}</span>
        </div>
      )}

      {narration && (
        <div className="panel" style={{ marginBottom: '24px', background: '#fafafa' }}>
          <div style={{ display: 'flex', gap: '8px', alignItems: 'center', marginBottom: '8px' }}>
            <Sparkles size={16} color="var(--violet)" />
            <b style={{ fontSize: '13px' }}>AI Roadmap Analysis</b>
          </div>
          <p style={{ fontSize: '13px', color: 'var(--ink)', lineHeight: '1.55', margin: 0 }}>
            {narration}
          </p>
        </div>
      )}

      {loading ? (
        <div style={{ textAlign: 'center', padding: '40px' }}>Computing optimal path & retrieving courses...</div>
      ) : roadmap.length === 0 ? (
        <div className="panel" style={{ textAlign: 'center', padding: '40px' }}>
          <CheckCircle2 size={40} color="var(--mint)" style={{ margin: '0 auto 12px' }} />
          <h3>All Prerequisites Met!</h3>
          <p style={{ color: 'var(--muted)', fontSize: '13px' }}>
            You have already mastered all prerequisites for <b>{goalSkill}</b>.
          </p>
        </div>
      ) : (
        <div className="roadmap-timeline">
          {roadmap.map((m) => (
            <div key={m.skill_id} className="milestone-node">
              <div className={`milestone-dot ${m.status}`} />
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '14px' }}>
                <div>
                  <span style={{ fontSize: '11px', textTransform: 'uppercase', letterSpacing: '0.08em', color: 'var(--muted)', fontWeight: 'bold' }}>
                    Milestone {m.order} · {m.domain || 'Backend'}
                  </span>
                  <h3 style={{ fontSize: '17px', margin: '4px 0 0' }}>{m.skill_name}</h3>
                  <small style={{ color: '#64748b', fontSize: '11px' }}>skill_id: {m.skill_id}</small>
                </div>

                {/* Live Feedback Action Buttons */}
                <div style={{ display: 'flex', gap: '8px' }}>
                  <button
                    onClick={() => handleFeedback(m.skill_id, 'completion')}
                    title="Mark module as completed"
                    style={{ background: '#dcfce7', color: '#15803d', padding: '6px 12px', borderRadius: '8px', fontSize: '11px', fontWeight: 'bold' }}
                  >
                    ✓ Complete
                  </button>
                  <button
                    onClick={() => handleFeedback(m.skill_id, 'quiz_score', 0.2)}
                    title="Simulate failing a quiz on this skill"
                    style={{ background: '#fee2e2', color: '#b91c1c', padding: '6px 12px', borderRadius: '8px', fontSize: '11px', fontWeight: 'bold' }}
                  >
                    ✗ Fail Quiz (0.2)
                  </button>
                  <button
                    onClick={() => handleFeedback(m.skill_id, 'skip')}
                    title="Skip this module"
                    style={{ background: '#f1f5f9', color: '#475569', padding: '6px 12px', borderRadius: '8px', fontSize: '11px' }}
                  >
                    Skip
                  </button>
                </div>
              </div>

              {/* Real Retrieved Courses */}
              <div style={{ marginTop: '14px' }}>
                <p style={{ fontSize: '11px', fontWeight: 'bold', color: 'var(--muted)', marginBottom: '8px' }}>
                  RECOMMENDED COURSES (RAG RETRIEVAL):
                </p>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                  {m.courses && m.courses.length > 0 ? (
                    m.courses.map((c) => (
                      <div key={c.course_id} className="course-pill">
                        <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
                          <span style={{ background: '#e0e7ff', color: '#4338ca', padding: '3px 8px', borderRadius: '6px', fontSize: '10px', fontWeight: 'bold' }}>
                            {c.provider}
                          </span>
                          <span style={{ fontWeight: 'bold' }}>{c.title}</span>
                          <span style={{ color: 'var(--muted)', fontSize: '11px' }}>({c.level})</span>
                        </div>
                        {c.url && (
                          <a href={c.url} target="_blank" rel="noreferrer" style={{ color: 'var(--violet)', display: 'flex', alignItems: 'center', gap: '4px', textDecoration: 'none', fontWeight: 'bold' }}>
                            View Course <ExternalLink size={13} />
                          </a>
                        )}
                      </div>
                    ))
                  ) : (
                    <div style={{ fontSize: '12px', color: 'var(--muted)' }}>No direct courses found in catalog.</div>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </section>
  )
}

/* =========================================================================
   4. "WHY NOT X?" GOAL COMPARATOR VIEW
   ========================================================================= */
function GoalComparisonView({ user }: { user: User | null }) {
  const [goalA, setGoalA] = useState('deployment')
  const [goalB, setGoalB] = useState('system_design_basics')
  const [compareData, setCompareData] = useState<CompareResponse | null>(null)
  const [loading, setLoading] = useState(false)

  const handleCompare = async () => {
    setLoading(true)
    try {
      const known = Object.entries(user?.confidence || {})
        .filter(([_, c]) => c >= 0.5)
        .map(([s]) => s)

      const res = await compareGoals(known, goalA, goalB)
      setCompareData(res)
    } catch (err: any) {
      alert('Error comparing goals: ' + err.message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    handleCompare()
  }, [goalA, goalB])

  return (
    <section className="module">
      <div className="module-title">
        <div>
          <p className="eyebrow">Decision & Trade-Off Engine</p>
          <h1>&quot;Why Not X?&quot; Goal Comparison</h1>
          <p className="subtitle">
            Compare two different career targets side-by-side to understand shared foundations, divergent skills, and learning time trade-offs.
          </p>
        </div>
      </div>

      <div className="panel" style={{ marginBottom: '24px' }}>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr auto', gap: '16px', alignItems: 'flex-end' }}>
          <div className="form-group">
            <label>Primary Goal (A):</label>
            <select value={goalA} onChange={(e) => setGoalA(e.target.value)}>
              <option value="deployment">Deployment (DevOps)</option>
              <option value="rest_apis">REST APIs</option>
              <option value="system_design_basics">System Design Basics</option>
              <option value="sqlalchemy">SQLAlchemy ORM</option>
            </select>
          </div>
          <div className="form-group">
            <label>Alternative Goal (B):</label>
            <select value={goalB} onChange={(e) => setGoalB(e.target.value)}>
              <option value="system_design_basics">System Design Basics</option>
              <option value="deployment">Deployment (DevOps)</option>
              <option value="rest_apis">REST APIs</option>
              <option value="sqlalchemy">SQLAlchemy ORM</option>
            </select>
          </div>
          <button className="primary" onClick={handleCompare} disabled={loading} style={{ height: '42px' }}>
            <Sparkles size={15} /> {loading ? 'Comparing...' : 'Run Diff'}
          </button>
        </div>
      </div>

      {compareData && (
        <>
          <div className="panel" style={{ background: 'linear-gradient(135deg, #f5f3ff, #faf5ff)', border: '1px solid #ddd6fe', marginBottom: '24px' }}>
            <h3 style={{ fontSize: '15px', display: 'flex', alignItems: 'center', gap: '8px', margin: '0 0 8px' }}>
              <Sparkles size={16} color="var(--violet)" /> AI Comparative Insight
            </h3>
            <p style={{ fontSize: '13px', lineHeight: '1.55', margin: 0, color: '#3b0764' }}>
              {compareData.explanation}
            </p>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '18px' }}>
            {/* Shared Skills */}
            <div className="panel">
              <p className="eyebrow" style={{ color: 'var(--mint)' }}>Shared Foundation</p>
              <h3 style={{ fontSize: '16px', margin: '0 0 12px' }}>Common Prerequisites ({compareData.shared_skills.length})</h3>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                {compareData.shared_skills.map((s) => (
                  <div key={s.skill_id} style={{ background: '#ecfdf5', padding: '10px 12px', borderRadius: '8px', fontSize: '12px', color: '#065f46' }}>
                    ✓ <b>{s.name}</b>
                  </div>
                ))}
              </div>
            </div>

            {/* Unique to Goal A */}
            <div className="panel">
              <p className="eyebrow" style={{ color: 'var(--violet)' }}>Unique to Goal A</p>
              <h3 style={{ fontSize: '16px', margin: '0 0 12px' }}>Only for {goalA} ({compareData.only_in_a.length})</h3>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                {compareData.only_in_a.map((s) => (
                  <div key={s.skill_id} style={{ background: '#f5f3ff', padding: '10px 12px', borderRadius: '8px', fontSize: '12px', color: '#4c1d95' }}>
                    • <b>{s.name}</b>
                  </div>
                ))}
              </div>
            </div>

            {/* Unique to Goal B */}
            <div className="panel">
              <p className="eyebrow" style={{ color: 'var(--orange)' }}>Unique to Goal B</p>
              <h3 style={{ fontSize: '16px', margin: '0 0 12px' }}>Only for {goalB} ({compareData.only_in_b.length})</h3>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                {compareData.only_in_b.map((s) => (
                  <div key={s.skill_id} style={{ background: '#fffbeb', padding: '10px 12px', borderRadius: '8px', fontSize: '12px', color: '#78350f' }}>
                    • <b>{s.name}</b>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </>
      )}
    </section>
  )
}

/* =========================================================================
   5. OTHER MODULE VIEWS (SKILLS MAP, RESUME, INTERVIEW, PROJECTS)
   ========================================================================= */
function SkillsMapView({ user, onNavigate }: { user: User | null; onNavigate: (v: string) => void }) {
  const conf = user?.confidence || { py_basics: 0.8, sql_basics: 0.6, rest_apis: 0.5, auth: 0.3 }
  return (
    <section className="module">
      <div className="module-title">
        <div>
          <p className="eyebrow">Confidence Spectrum</p>
          <h1>Skill Capability Map</h1>
          <p className="subtitle">Calculated from quiz evaluations, completions, and chat extraction.</p>
        </div>
        <button className="primary" onClick={() => onNavigate('Career Assessment')}>
          <Plus size={16} /> Assess More Skills
        </button>
      </div>

      <div className="stat-grid">
        {[
          ['Skills Tracked', Object.keys(conf).length.toString(), 'In profile'],
          ['Mastered (>=50%)', Object.values(conf).filter((v) => v >= 0.5).length.toString(), 'Ready for projects'],
          ['Priority Gaps', Object.values(conf).filter((v) => v < 0.5).length.toString(), 'Needs focus'],
          ['Avg Confidence', `${Math.round(Object.values(conf).reduce((a,b)=>a+b,0)/Object.keys(conf).length*100)}%`, 'Growth index']
        ].map(([a,b,c]) => (
          <div className="stat-card" key={a}><small>{a}</small><strong>{b}</strong><span>{c}</span></div>
        ))}
      </div>

      <div className="panel">
        <h3 style={{ fontSize: '16px', marginBottom: '16px' }}>Skill Mastery List</h3>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
          {Object.entries(conf).map(([skill, val]) => (
            <div key={skill} style={{ display: 'grid', gridTemplateColumns: '180px 1fr 60px', alignItems: 'center', gap: '16px' }}>
              <b style={{ fontSize: '13px' }}>{skill}</b>
              <div className="progress"><span style={{ width: `${val * 100}%`, background: val >= 0.5 ? 'var(--mint)' : 'var(--orange)' }} /></div>
              <strong style={{ fontSize: '13px', textAlign: 'right' }}>{Math.round(val * 100)}%</strong>
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}

function ProjectsView() {
  return (
    <section className="module">
      <div className="module-title">
        <div>
          <p className="eyebrow">Proof of Work</p>
          <h1>Project Portfolio</h1>
          <p className="subtitle">Evidence backing your mastered skills.</p>
        </div>
      </div>
      <div className="stat-grid">
        {[['Active Projects','03','In progress'],['Portfolio Strength','82%','Strong'],['Verified Skills','8','Tested'],['Next Milestone','Nov 24','API Gateway']].map(([a,b,c]) => (
          <div className="stat-card" key={a}><small>{a}</small><strong>{b}</strong><span>{c}</span></div>
        ))}
      </div>
    </section>
  )
}

function ResumeView({ user }: { user: User | null }) {
  return (
    <section className="module">
      <div className="module-title">
        <div>
          <p className="eyebrow">Career Materials</p>
          <h1>Resume & ATS Keyword Optimizer</h1>
          <p className="subtitle">Aligned to target role: {user?.target_role || 'Backend Developer'}.</p>
        </div>
      </div>
      <div className="panel">
        <h3>Target Keywords to Include</h3>
        <p style={{ fontSize: '13px', color: 'var(--muted)' }}>FastAPI, Docker, PostgreSQL, REST APIs, CI/CD Deployment, SQLAlchemy, JWT Auth.</p>
      </div>
    </section>
  )
}

function InterviewPrepView() {
  return (
    <section className="module">
      <div className="module-title">
        <div>
          <p className="eyebrow">Interview Readiness</p>
          <h1>Backend Technical Interview Simulator</h1>
          <p className="subtitle">Practice system design and database indexing explanations.</p>
        </div>
      </div>
      <div className="panel">
        <h3>Recommended Focus Questions</h3>
        <ul>
          <li>Explain the difference between SQL joins and indexing strategies.</li>
          <li>How does JWT authentication work and how do you prevent token tampering?</li>
          <li>What are the core steps to deploy and monitor a containerized Flask/FastAPI service?</li>
        </ul>
      </div>
    </section>
  )
}

/* =========================================================================
   6. AI CAREER COPILOT (CHAT & NATURAL LANGUAGE INTAKE)
   ========================================================================= */
function CareerCopilot({ user, onNavigate }: { user: User | null; onNavigate: (v: string) => void }) {
  const [messages, setMessages] = useState<Array<{ id: string; role: 'user' | 'assistant'; text: string }>>([
    { id: '1', role: 'assistant', text: 'Hi! I am your NEXORA Career Copilot. Tell me your target career goal or ask about specific skill prerequisites!' }
  ])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)

  const handleSend = async (textToSend?: string) => {
    const text = (textToSend || input).trim()
    if (!text || loading) return

    const userMsg = { id: Date.now().toString(), role: 'user' as const, text }
    setMessages((prev) => [...prev, userMsg])
    setInput('')
    setLoading(true)

    try {
      const res = await sendCopilotMessage(text, user?.id)
      const botMsg = { id: (Date.now() + 1).toString(), role: 'assistant' as const, text: res.reply }
      setMessages((prev) => [...prev, botMsg])

      // If intent extracted a goal, prompt navigation
      if (res.extracted_data && res.extracted_data.goal_skill) {
        setTimeout(() => {
          onNavigate('Learning Roadmap')
        }, 1200)
      }
    } catch (err: any) {
      setMessages((prev) => [...prev, { id: Date.now().toString(), role: 'assistant', text: 'Copilot error: ' + err.message }])
    } finally {
      setLoading(false)
    }
  }

  return (
    <aside className="copilot">
      <div className="copilot-head">
        <div>
          <p className="eyebrow">AI Career Copilot</p>
          <h2>Ask NEXORA</h2>
        </div>
        <span className="live-dot">Online</span>
      </div>

      <p className="copilot-intro">State your goals in natural language or ask for prerequisite guidance.</p>

      <div className="suggestions">
        <button onClick={() => handleSend('I know Python and want to learn deployment in 2 months')}>
          🎯 Goal Intake
        </button>
        <button onClick={() => handleSend('What should I prioritize this week?')}>
          ⚡ Priorities
        </button>
        <button onClick={() => handleSend('How can I prepare for backend interviews?')}>
          🎙️ Interviews
        </button>
      </div>

      <div className="chat-transcript">
        {messages.map((m) => (
          <div key={m.id} className={`chat-message ${m.role}`}>
            <span>{m.role === 'user' ? 'You' : 'NEXORA AI'}</span>
            <p>{m.text}</p>
          </div>
        ))}
        {loading && (
          <div className="chat-message assistant">
            <span>NEXORA AI</span>
            <p>Analyzing skill graph & intent...</p>
          </div>
        )}
      </div>

      <form
        className="copilot-form"
        onSubmit={(e) => { e.preventDefault(); handleSend(); }}
      >
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask or state your goal..."
        />
        <button type="submit" disabled={!input.trim() || loading}>
          <MessageSquare size={16} />
        </button>
      </form>
    </aside>
  )
}
