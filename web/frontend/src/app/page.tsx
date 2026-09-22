'use client'

import { useEffect, useState } from 'react'
import { Activity, Users, MessageSquare, Clock, AlertTriangle, TrendingUp, BarChart3 } from 'lucide-react'

interface Stats {
  tickets: {
    total: number
    open: number
    closed: number
  }
  users: {
    total: number
    staff: number
  }
}

interface SLAData {
  total_events: number
  met_events: number
  breached_events: number
  compliance_rate: number
}

interface StaffPerformance {
  id: number
  name: string
  specialization: string | null
  tickets_claimed: number
  tickets_resolved: number
  resolved_in_period: number
  avg_response_time_seconds: number | null
}

export default function Dashboard() {
  const [stats, setStats] = useState<Stats | null>(null)
  const [slaData, setSlaData] = useState<SLAData | null>(null)
  const [staffPerformance, setStaffPerformance] = useState<StaffPerformance[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    // Fetch all analytics data
    Promise.all([
      fetch('/api/v1/stats').then(res => res.json()),
      fetch('/api/v1/sla/compliance?days=30').then(res => res.json()),
      fetch('/api/v1/analytics/staff-performance?days=30').then(res => res.json()),
    ])
      .then(([statsData, slaData, staffData]) => {
        setStats(statsData)
        setSlaData(slaData)
        setStaffPerformance(staffData.staff || [])
        setLoading(false)
      })
      .catch(err => {
        console.error('Failed to fetch analytics:', err)
        setLoading(false)
      })
  }, [])

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow-sm border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            <div className="flex items-center">
              <MessageSquare className="h-8 w-8 text-brand-600" />
              <h1 className="ml-3 text-2xl font-bold text-gray-900">Reyex Support</h1>
            </div>
            <div className="flex items-center space-x-4">
              <span className="text-sm text-gray-600">Connected as Staff</span>
              <div className="h-8 w-8 rounded-full bg-brand-600 flex items-center justify-center text-white font-semibold">
                S
              </div>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="mb-8">
          <h2 className="text-3xl font-bold text-gray-900">Dashboard</h2>
          <p className="mt-2 text-gray-600">Overview of support ticket activity</p>
        </div>

        {loading ? (
          <div className="text-center py-12">
            <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-brand-600"></div>
            <p className="mt-4 text-gray-600">Loading analytics...</p>
          </div>
        ) : (
          <>
            {/* Stats Cards */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
              {/* Total Tickets */}
              <div className="bg-white rounded-lg shadow p-6">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm font-medium text-gray-600">Total Tickets</p>
                    <p className="text-3xl font-bold text-gray-900 mt-2">{stats?.tickets.total || 0}</p>
                  </div>
                  <div className="h-12 w-12 rounded-full bg-brand-100 flex items-center justify-center">
                    <MessageSquare className="h-6 w-6 text-brand-600" />
                  </div>
                </div>
              </div>

              {/* Open Tickets */}
              <div className="bg-white rounded-lg shadow p-6">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm font-medium text-gray-600">Open Tickets</p>
                    <p className="text-3xl font-bold text-brand-600 mt-2">{stats?.tickets.open || 0}</p>
                  </div>
                  <div className="h-12 w-12 rounded-full bg-green-100 flex items-center justify-center">
                    <Activity className="h-6 w-6 text-green-600" />
                  </div>
                </div>
              </div>

              {/* Total Users */}
              <div className="bg-white rounded-lg shadow p-6">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm font-medium text-gray-600">Total Users</p>
                    <p className="text-3xl font-bold text-gray-900 mt-2">{stats?.users.total || 0}</p>
                  </div>
                  <div className="h-12 w-12 rounded-full bg-blue-100 flex items-center justify-center">
                    <Users className="h-6 w-6 text-blue-600" />
                  </div>
                </div>
              </div>

              {/* Staff Members */}
              <div className="bg-white rounded-lg shadow p-6">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm font-medium text-gray-600">Staff Members</p>
                    <p className="text-3xl font-bold text-gray-900 mt-2">{stats?.users.staff || 0}</p>
                  </div>
                  <div className="h-12 w-12 rounded-full bg-purple-100 flex items-center justify-center">
                    <Clock className="h-6 w-6 text-purple-600" />
                  </div>
                </div>
              </div>
            </div>

            {/* SLA Compliance Card */}
            <div className="bg-white rounded-lg shadow p-6 mb-8">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-lg font-semibold text-gray-900">SLA Compliance (30 days)</h3>
                <div className="flex items-center space-x-2">
                  <TrendingUp className="h-5 w-5 text-green-600" />
                  <span className="text-2xl font-bold text-green-600">
                    {slaData?.compliance_rate.toFixed(1) || 0}%
                  </span>
                </div>
              </div>
              <div className="grid grid-cols-3 gap-4">
                <div className="text-center">
                  <p className="text-sm text-gray-600">Total Events</p>
                  <p className="text-xl font-semibold text-gray-900">{slaData?.total_events || 0}</p>
                </div>
                <div className="text-center">
                  <p className="text-sm text-gray-600">Met</p>
                  <p className="text-xl font-semibold text-green-600">{slaData?.met_events || 0}</p>
                </div>
                <div className="text-center">
                  <p className="text-sm text-gray-600">Breached</p>
                  <p className="text-xl font-semibold text-red-600">{slaData?.breached_events || 0}</p>
                </div>
              </div>
            </div>

            {/* Staff Performance */}
            <div className="bg-white rounded-lg shadow mb-8">
              <div className="px-6 py-4 border-b border-gray-200">
                <h3 className="text-lg font-semibold text-gray-900">Staff Performance (30 days)</h3>
              </div>
              <div className="p-6">
                {staffPerformance.length > 0 ? (
                  <div className="space-y-4">
                    {staffPerformance.map((staff) => (
                      <div key={staff.id} className="flex items-center justify-between p-4 bg-gray-50 rounded-lg">
                        <div className="flex items-center space-x-4">
                          <div className="h-10 w-10 rounded-full bg-brand-100 flex items-center justify-center text-brand-600 font-semibold">
                            {staff.name.charAt(0).toUpperCase()}
                          </div>
                          <div>
                            <p className="font-medium text-gray-900">{staff.name}</p>
                            <p className="text-sm text-gray-600">{staff.specialization || 'General'}</p>
                          </div>
                        </div>
                        <div className="flex items-center space-x-8">
                          <div className="text-center">
                            <p className="text-sm text-gray-600">Resolved</p>
                            <p className="font-semibold text-gray-900">{staff.resolved_in_period}</p>
                          </div>
                          <div className="text-center">
                            <p className="text-sm text-gray-600">Avg Response</p>
                            <p className="font-semibold text-gray-900">
                              {staff.avg_response_time_seconds 
                                ? `${Math.round(staff.avg_response_time_seconds / 60)}m`
                                : 'N/A'}
                            </p>
                          </div>
                          <div className="text-center">
                            <p className="text-sm text-gray-600">Total Resolved</p>
                            <p className="font-semibold text-gray-900">{staff.tickets_resolved}</p>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-gray-600">No staff performance data available.</p>
                )}
              </div>
            </div>

            {/* Quick Stats Grid */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div className="bg-white rounded-lg shadow p-6">
                <div className="flex items-center space-x-3 mb-4">
                  <BarChart3 className="h-6 w-6 text-brand-600" />
                  <h3 className="text-lg font-semibold text-gray-900">Analytics</h3>
                </div>
                <p className="text-gray-600">
                  Detailed analytics including ticket trends, priority distribution, and hourly activity 
                  are available through the API endpoints.
                </p>
              </div>

              <div className="bg-white rounded-lg shadow p-6">
                <div className="flex items-center space-x-3 mb-4">
                  <AlertTriangle className="h-6 w-6 text-yellow-600" />
                  <h3 className="text-lg font-semibold text-gray-900">SLA Breaches</h3>
                </div>
                <p className="text-gray-600">
                  Monitor SLA compliance and breach alerts in real-time. Configure SLA targets 
                  per priority level in bot settings.
                </p>
              </div>
            </div>
          </>
        )}
      </main>
    </div>
  )
}
