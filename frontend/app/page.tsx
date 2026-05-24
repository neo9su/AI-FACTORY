import Link from 'next/link';

export default function Home() {
  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-indigo-50 to-purple-50">
      <div className="container mx-auto px-4 py-16">
        {/* Hero Section */}
        <div className="text-center max-w-4xl mx-auto mb-16">
          <h1 className="text-6xl font-bold text-gray-900 mb-6">
            Autonomous AI Software Factory
          </h1>
          <p className="text-2xl text-gray-600 mb-8">
            Input requirements. AI builds, tests, and deploys automatically.
          </p>
          <Link
            href="/projects/new"
            className="inline-block px-8 py-4 bg-blue-600 text-white text-lg font-semibold rounded-lg hover:bg-blue-700 transition-colors shadow-lg hover:shadow-xl"
          >
            Create Project
          </Link>
        </div>

        {/* Features Section */}
        <div className="max-w-6xl mx-auto grid md:grid-cols-2 lg:grid-cols-4 gap-8">
          <div className="bg-white rounded-xl p-6 shadow-md hover:shadow-lg transition-shadow">
            <div className="w-12 h-12 bg-blue-100 rounded-lg flex items-center justify-center mb-4">
              <span className="text-2xl">📋</span>
            </div>
            <h3 className="text-xl font-semibold text-gray-900 mb-2">
              Requirements Analysis
            </h3>
            <p className="text-gray-600">
              AI analyzes your requirements and generates a detailed PRD with
              architecture decisions.
            </p>
          </div>

          <div className="bg-white rounded-xl p-6 shadow-md hover:shadow-lg transition-shadow">
            <div className="w-12 h-12 bg-purple-100 rounded-lg flex items-center justify-center mb-4">
              <span className="text-2xl">⚙️</span>
            </div>
            <h3 className="text-xl font-semibold text-gray-900 mb-2">
              Auto Development
            </h3>
            <p className="text-gray-600">
              Claude Code autonomously writes production-ready code following
              best practices.
            </p>
          </div>

          <div className="bg-white rounded-xl p-6 shadow-md hover:shadow-lg transition-shadow">
            <div className="w-12 h-12 bg-green-100 rounded-lg flex items-center justify-center mb-4">
              <span className="text-2xl">✅</span>
            </div>
            <h3 className="text-xl font-semibold text-gray-900 mb-2">
              Auto Testing
            </h3>
            <p className="text-gray-600">
              Comprehensive test suites are generated and executed automatically
              with intelligent retries.
            </p>
          </div>

          <div className="bg-white rounded-xl p-6 shadow-md hover:shadow-lg transition-shadow">
            <div className="w-12 h-12 bg-teal-100 rounded-lg flex items-center justify-center mb-4">
              <span className="text-2xl">🚀</span>
            </div>
            <h3 className="text-xl font-semibold text-gray-900 mb-2">
              Auto Deployment
            </h3>
            <p className="text-gray-600">
              Your project is deployed to preview environments with one-click
              production release.
            </p>
          </div>
        </div>

        {/* How It Works */}
        <div className="max-w-4xl mx-auto mt-16 bg-white rounded-xl p-8 shadow-md">
          <h2 className="text-3xl font-bold text-gray-900 mb-6 text-center">
            How It Works
          </h2>
          <div className="space-y-4">
            <div className="flex items-start space-x-4">
              <div className="flex-shrink-0 w-8 h-8 bg-blue-500 text-white rounded-full flex items-center justify-center font-bold">
                1
              </div>
              <div>
                <h4 className="font-semibold text-gray-900">
                  Describe Your Project
                </h4>
                <p className="text-gray-600">
                  Provide your requirements, goals, and preferences.
                </p>
              </div>
            </div>
            <div className="flex items-start space-x-4">
              <div className="flex-shrink-0 w-8 h-8 bg-blue-500 text-white rounded-full flex items-center justify-center font-bold">
                2
              </div>
              <div>
                <h4 className="font-semibold text-gray-900">
                  AI Analyzes & Plans
                </h4>
                <p className="text-gray-600">
                  The system generates a PRD, architecture, and task breakdown.
                </p>
              </div>
            </div>
            <div className="flex items-start space-x-4">
              <div className="flex-shrink-0 w-8 h-8 bg-blue-500 text-white rounded-full flex items-center justify-center font-bold">
                3
              </div>
              <div>
                <h4 className="font-semibold text-gray-900">
                  Autonomous Development
                </h4>
                <p className="text-gray-600">
                  Code is written, tested, and refined automatically.
                </p>
              </div>
            </div>
            <div className="flex items-start space-x-4">
              <div className="flex-shrink-0 w-8 h-8 bg-blue-500 text-white rounded-full flex items-center justify-center font-bold">
                4
              </div>
              <div>
                <h4 className="font-semibold text-gray-900">
                  Deploy & Deliver
                </h4>
                <p className="text-gray-600">
                  Your project is deployed with full delivery report.
                </p>
              </div>
            </div>
          </div>
        </div>

        {/* CTA Section */}
        <div className="text-center mt-16">
          <Link
            href="/dashboard"
            className="inline-block px-6 py-3 bg-white text-indigo-600 text-lg font-semibold rounded-lg hover:bg-gray-50 transition-colors shadow-md mr-4"
          >
            📊 Dashboard
          </Link>
          <Link
            href="/projects"
            className="inline-block px-6 py-3 bg-white text-blue-600 text-lg font-semibold rounded-lg hover:bg-gray-50 transition-colors shadow-md mr-4"
          >
            View Projects
          </Link>
          <Link
            href="/projects/new"
            className="inline-block px-6 py-3 bg-blue-600 text-white text-lg font-semibold rounded-lg hover:bg-blue-700 transition-colors shadow-md mr-4"
          >
            Get Started
          </Link>
          <Link
            href="/settings"
            className="inline-block px-6 py-3 bg-white/20 text-white text-lg font-semibold rounded-lg hover:bg-white/30 transition-colors border border-white/40"
          >
            ⚙️ Settings
          </Link>
        </div>
      </div>
    </div>
  );
}
