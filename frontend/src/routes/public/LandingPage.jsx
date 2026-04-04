// Landing Page Component
import { Link } from "react-router-dom";
import Button from "../../components/ui/Button";
import { Card, CardContent } from "../../components/ui/Card";

const FEATURES = [
  {
    icon: (
      <svg
        className="w-8 h-8"
        fill="none"
        stroke="currentColor"
        viewBox="0 0 24 24"
      >
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth={2}
          d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"
        />
      </svg>
    ),
    title: "Realistic CBT Experience",
    description:
      "Practice on an interface that mirrors the actual exam environment.",
  },
  {
    icon: (
      <svg
        className="w-8 h-8"
        fill="none"
        stroke="currentColor"
        viewBox="0 0 24 24"
      >
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth={2}
          d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"
        />
      </svg>
    ),
    title: "Precision Timers",
    description:
      "Section-wise and overall timers that work exactly like the real exam.",
  },
  {
    icon: (
      <svg
        className="w-8 h-8"
        fill="none"
        stroke="currentColor"
        viewBox="0 0 24 24"
      >
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth={2}
          d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"
        />
      </svg>
    ),
    title: "Detailed Analytics",
    description:
      "In-depth performance analysis to identify your strengths and weaknesses.",
  },
  {
    icon: (
      <svg
        className="w-8 h-8"
        fill="none"
        stroke="currentColor"
        viewBox="0 0 24 24"
      >
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth={2}
          d="M12 6V4m0 2a2 2 0 100 4m0-4a2 2 0 110 4m-6 8a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4m6 6v10m6-2a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4"
        />
      </svg>
    ),
    title: "Customizable Tests",
    description:
      "Choose your topics, difficulty, and test duration as per your needs.",
  },
];

const EXAMS = [
  "SSC CGL",
  "SSC CHSL",
  "IBPS PO",
  "IBPS Clerk",
  "RRB NTPC",
  "SBI PO",
];

const STATS = [
  { value: "50K+", label: "Active Users" },
  { value: "100K+", label: "Tests Taken" },
  { value: "5000+", label: "Questions" },
  { value: "4.8", label: "User Rating" },
];

export default function LandingPage() {
  return (
    <div className="flex-1">
      {/* Hero Section */}
      <section className="relative bg-gradient-to-br from-blue-600 via-blue-700 to-indigo-800 text-white pt-24 pb-20">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center max-w-3xl mx-auto">
            <h1 className="text-4xl sm:text-5xl lg:text-6xl font-bold leading-tight">
              Practice Like You Test,
              <span className="text-blue-200"> Score Like a Topper</span>
            </h1>
            <p className="mt-6 text-lg sm:text-xl text-blue-100">
              India's most realistic Computer Based Test (CBT) mock platform.
              Experience the exact exam interface, precision timers, and
              detailed analytics.
            </p>
            <p className="mt-3 text-base text-blue-200">
              Looking for TS EAPCET mock tests, AI mock test generators, or
              exam-like practice for SSC and IBPS? MockMitra helps you practice
              smarter.
            </p>
            <div className="mt-10 flex flex-col sm:flex-row items-center justify-center gap-4">
              <Link to="/signup">
                <Button
                  size="lg"
                  variant="ghost"
                  className="bg-white text-blue-600 hover:bg-blue-50 font-semibold px-8 shadow-lg"
                >
                  Start Free Practice
                </Button>
              </Link>
              <Link to="/login">
                <Button
                  size="lg"
                  variant="ghost"
                  className="border-2 border-white text-white hover:bg-white/10 px-8"
                >
                  Sign In
                </Button>
              </Link>
            </div>

            {/* Exam Tags */}
            <div className="mt-12 flex flex-wrap items-center justify-center gap-3">
              {EXAMS.map((exam) => (
                <span
                  key={exam}
                  className="px-4 py-1.5 bg-white/10 backdrop-blur rounded-full text-sm font-medium"
                >
                  {exam}
                </span>
              ))}
            </div>
          </div>
        </div>

        {/* Wave divider */}
        <div className="absolute bottom-0 left-0 right-0">
          <svg
            viewBox="0 0 1440 120"
            fill="none"
            xmlns="http://www.w3.org/2000/svg"
          >
            <path
              d="M0 120L60 110C120 100 240 80 360 70C480 60 600 60 720 65C840 70 960 80 1080 85C1200 90 1320 90 1380 90L1440 90V120H1380C1320 120 1200 120 1080 120C960 120 840 120 720 120C600 120 480 120 360 120C240 120 120 120 60 120H0Z"
              fill="#F9FAFB"
            />
          </svg>
        </div>
      </section>

      {/* Stats Section */}
      <section className="bg-gray-50 py-12">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-8">
            {STATS.map((stat) => (
              <div key={stat.label} className="text-center">
                <p className="text-3xl sm:text-4xl font-bold text-blue-600">
                  {stat.value}
                </p>
                <p className="text-gray-600 mt-1">{stat.label}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Features Section */}
      <section className="py-20 bg-white">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-16">
            <h2 className="text-3xl sm:text-4xl font-bold text-gray-900">
              Why Choose MockMitra?
            </h2>
            <p className="mt-4 text-lg text-gray-600 max-w-2xl mx-auto">
              We've built the most authentic exam simulation platform to help
              you succeed in your competitive exams.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-8">
            {FEATURES.map((feature, index) => (
              <Card
                key={index}
                className="text-center hover:shadow-lg transition-shadow"
              >
                <CardContent className="p-6">
                  <div className="w-16 h-16 bg-blue-100 text-blue-600 rounded-xl flex items-center justify-center mx-auto mb-4">
                    {feature.icon}
                  </div>
                  <h3 className="text-lg font-semibold text-gray-900 mb-2">
                    {feature.title}
                  </h3>
                  <p className="text-gray-600 text-sm">{feature.description}</p>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="py-20 bg-gradient-to-r from-blue-600 to-blue-800 text-white">
        <div className="max-w-4xl mx-auto px-4 text-center">
          <h2 className="text-3xl sm:text-4xl font-bold">
            Ready to Start Your Preparation?
          </h2>
          <p className="mt-4 text-lg text-blue-100">
            Join thousands of aspirants who are already practicing on MockMitra.
            Get started for free today.
          </p>
          <div className="mt-8">
            <Link to="/signup">
              <Button
                size="lg"
                variant="ghost"
                className="bg-white text-blue-600 hover:bg-gray-100 px-8 font-semibold shadow-lg"
              >
                Create Free Account
              </Button>
            </Link>
          </div>
        </div>
      </section>
    </div>
  );
}
