import { createContext, useContext, useState, useEffect, ReactNode } from 'react'
import { api } from '../lib/api'

interface User {
  user_id: string
  email: string
  full_name: string
  role: string
  is_active: boolean
}

interface AuthContextType {
  user: User | null
  loading: boolean
  login: (email: string, password: string) => Promise<void>
  register: (data: {
    email: string
    password: string
    full_name: string
    company_name?: string
  }) => Promise<void>
  logout: () => void
}

const AuthContext = createContext<AuthContextType | undefined>(undefined)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    // Check if user is logged in on mount
    const accessToken = localStorage.getItem('accessToken')
    const userStr = localStorage.getItem('user')

    if (accessToken && userStr) {
      try {
        setUser(JSON.parse(userStr))
      } catch (e) {
        localStorage.removeItem('accessToken')
        localStorage.removeItem('refreshToken')
        localStorage.removeItem('user')
      }
    }

    setLoading(false)
  }, [])

  const login = async (email: string, password: string) => {
    const response = await api.login(email, password)
    const { access_token, refresh_token, user: userData } = response.data

    localStorage.setItem('accessToken', access_token)
    localStorage.setItem('refreshToken', refresh_token)
    localStorage.setItem('user', JSON.stringify(userData))

    setUser(userData)
  }

  const register = async (data: {
    email: string
    password: string
    full_name: string
    company_name?: string
  }) => {
    const response = await api.register(data)
    const { access_token, refresh_token, user: userData } = response.data

    localStorage.setItem('accessToken', access_token)
    localStorage.setItem('refreshToken', refresh_token)
    localStorage.setItem('user', JSON.stringify(userData))

    setUser(userData)
  }

  const logout = () => {
    localStorage.removeItem('accessToken')
    localStorage.removeItem('refreshToken')
    localStorage.removeItem('user')
    setUser(null)
  }

  return (
    <AuthContext.Provider value={{ user, loading, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}
