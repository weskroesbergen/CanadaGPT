/**
 * Contact page
 */

import { Card } from '@canadagpt/design-system';
import { Mail, MessageSquare, Github, ExternalLink } from 'lucide-react';

export const metadata = {
  title: 'Contact Us - CanadaGPT',
  description: 'Get in touch with the CanadaGPT team for support, feedback, or collaboration opportunities.',
};

export default function ContactPage() {
  return (
    <div className="page-container max-w-4xl mx-auto">
      {/* Header */}
      <div className="text-center mb-12">
        <MessageSquare className="h-16 w-16 text-accent-red mx-auto mb-4" />
        <h1 className="text-4xl font-bold text-text-primary mb-4">Get in Touch</h1>
        <p className="text-xl text-text-secondary max-w-2xl mx-auto">
          We'd love to hear from you. Whether you have questions, feedback, or want to contribute.
        </p>
        <div className="mt-6 text-text-secondary">
          <p className="font-semibold text-text-primary mb-1">Northern Variables</p>
          <p>305-717 Richmond St.</p>
          <p>London, ON N6A 1S2</p>
        </div>
      </div>

      {/* Contact Methods */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
        <Card elevated className="hover:border-accent-red transition-colors">
          <Mail className="h-10 w-10 text-accent-red mb-4" />
          <h3 className="text-xl font-semibold text-text-primary mb-2">Email Us</h3>
          <p className="text-text-secondary mb-4">
            For general inquiries, feedback, or support questions.
          </p>
          <a
            href="mailto:info@northernvariables.ca"
            className="inline-flex items-center gap-2 text-accent-red hover:text-accent-red-hover font-semibold"
          >
            info@northernvariables.ca <ExternalLink className="h-4 w-4" />
          </a>
        </Card>

        <Card elevated className="hover:border-accent-red transition-colors">
          <Github className="h-10 w-10 text-accent-red mb-4" />
          <h3 className="text-xl font-semibold text-text-primary mb-2">GitHub Issues</h3>
          <p className="text-text-secondary mb-4">
            Report bugs, request features, or contribute to the project.
          </p>
          <a
            href="https://github.com/matthewdufresne/FedMCP/issues"
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-2 text-accent-red hover:text-accent-red-hover font-semibold"
          >
            Open an Issue <ExternalLink className="h-4 w-4" />
          </a>
        </Card>
      </div>

      {/* FAQ / Common Questions */}
      <Card className="mb-8">
        <h2 className="text-2xl font-bold text-text-primary mb-6">Frequently Asked Questions</h2>
        <div className="space-y-6">
          <div>
            <h3 className="text-lg font-semibold text-text-primary mb-2">
              How often is the data updated?
            </h3>
            <p className="text-text-secondary">
              Our platform syncs data daily from official government sources. Hansard debates are
              typically available 1-2 days after they occur, while MP information and lobbying data
              are updated nightly.
            </p>
          </div>

          <div>
            <h3 className="text-lg font-semibold text-text-primary mb-2">
              Is CanadaGPT affiliated with the Government of Canada?
            </h3>
            <p className="text-text-secondary">
              No, CanadaGPT is an independent, open-source project. We aggregate data from publicly
              available government sources but are not affiliated with any government entity.
            </p>
          </div>

          <div>
            <h3 className="text-lg font-semibold text-text-primary mb-2">
              Can I use your data for my own project?
            </h3>
            <p className="text-text-secondary">
              Yes! All government data we aggregate is public domain. Our GraphQL API is available
              for developers, and our entire codebase is open source on GitHub. Please credit
              CanadaGPT if you use our platform.
            </p>
          </div>

          <div>
            <h3 className="text-lg font-semibold text-text-primary mb-2">
              How can I contribute to the project?
            </h3>
            <p className="text-text-secondary">
              We welcome contributions! Check out our{' '}
              <a
                href="https://github.com/matthewdufresne/FedMCP"
                target="_blank"
                rel="noopener noreferrer"
                className="text-accent-red hover:text-accent-red-hover"
              >
                GitHub repository
              </a>{' '}
              for open issues, or reach out via email to discuss larger contributions.
            </p>
          </div>

          <div>
            <h3 className="text-lg font-semibold text-text-primary mb-2">
              I found incorrect data. How do I report it?
            </h3>
            <p className="text-text-secondary">
              Please{' '}
              <a
                href="https://github.com/matthewdufresne/FedMCP/issues"
                target="_blank"
                rel="noopener noreferrer"
                className="text-accent-red hover:text-accent-red-hover"
              >
                open a GitHub issue
              </a>{' '}
              with details about the incorrect data. Include the page URL and what you expected to
              see. We investigate all data quality reports.
            </p>
          </div>
        </div>
      </Card>

      {/* Support the Project */}
      <Card className="text-center bg-bg-overlay border-border-emphasis">
        <h2 className="text-2xl font-bold text-text-primary mb-3">Support the Project</h2>
        <p className="text-text-secondary mb-4 max-w-2xl mx-auto">
          CanadaGPT is a volunteer-driven, open-source project. We rely on community contributions
          to maintain and improve the platform.
        </p>
        <div className="flex flex-col sm:flex-row gap-3 justify-center">
          <a
            href="https://github.com/matthewdufresne/FedMCP"
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center justify-center gap-2 px-6 py-3 bg-accent-red text-white rounded-lg hover:bg-accent-red-hover transition-colors font-semibold"
          >
            <Github className="h-5 w-5" />
            Contribute on GitHub
          </a>
          <a
            href="mailto:info@northernvariables.ca?subject=CanadaGPT Support"
            className="inline-flex items-center justify-center gap-2 px-6 py-3 border border-border-emphasis text-text-primary rounded-lg hover:border-accent-red transition-colors font-semibold"
          >
            <Mail className="h-5 w-5" />
            Get in Touch
          </a>
        </div>
      </Card>
    </div>
  );
}
