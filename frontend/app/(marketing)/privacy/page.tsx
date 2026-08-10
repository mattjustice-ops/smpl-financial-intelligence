import type { Metadata } from "next";
import Link from "next/link";

import { LandingFooter } from "@/components/landing/LandingFooter";
import { SALES_EMAIL } from "@/components/landing/constants";
import { sitePageUrl } from "@/lib/site";

const title = "Privacy Policy | SMPL.ai";
const description =
  "How SMPL.ai collects, uses, and shares information from our website, advertising, lead forms, and product.";
const url = sitePageUrl("/privacy");

export const metadata: Metadata = {
  title: { absolute: title },
  description,
  alternates: { canonical: url },
  openGraph: { title, description, url },
  twitter: { title, description },
};

const LAST_UPDATED = "August 10, 2026";

function Section({
  id,
  title: heading,
  children,
}: {
  id: string;
  title: string;
  children: React.ReactNode;
}) {
  return (
    <section id={id} className="scroll-mt-28">
      <h2 className="text-xl font-semibold tracking-tight text-white">{heading}</h2>
      <div className="mt-3 space-y-3 text-base leading-relaxed text-slate-300">{children}</div>
    </section>
  );
}

export default function PrivacyPage() {
  return (
    <>
      <main className="px-6 py-16 md:py-24">
        <article className="mx-auto max-w-3xl">
          <p className="text-sm font-semibold uppercase tracking-widest text-teal-400">Legal</p>
          <h1 className="mt-3 text-3xl font-semibold tracking-tight text-white md:text-5xl">
            Privacy Policy
          </h1>
          <p className="mt-4 text-lg text-slate-400">
            This notice explains how SMPL.ai (&quot;SMPL,&quot; &quot;we,&quot; &quot;us&quot;) handles
            information when you visit{" "}
            <a href="https://www.smpl-ai.com" className="text-teal-300 hover:text-teal-200">
              www.smpl-ai.com
            </a>
            , interact with our ads, submit a demo or quote request, or use our product.
          </p>
          <p className="mt-2 text-sm text-slate-500">Last updated: {LAST_UPDATED}</p>

          <div className="mt-12 space-y-10">
            <Section id="who" title="1. Who we are">
              <p>
                SMPL provides B2B financial intelligence software for SaaS finance teams. For
                privacy questions, contact us at{" "}
                <a
                  href={`mailto:${SALES_EMAIL}?subject=${encodeURIComponent("Privacy inquiry")}`}
                  className="text-teal-300 hover:text-teal-200"
                >
                  {SALES_EMAIL}
                </a>
                .
              </p>
            </Section>

            <Section id="collect" title="2. Information we collect">
              <p>
                <span className="font-medium text-white">Website and lead forms.</span> When you
                request a demo or quote, we collect contact and business details you provide, such
                as name, work email, phone number, company, job title, location, how reliable your
                finance data is today, and a description of your primary needs. If you continue to
                scheduling, Google Calendar may also collect information you enter there.
              </p>
              <p>
                <span className="font-medium text-white">Advertising and site technology.</span> Our
                marketing pages load a Google Ads tag so we can measure ad clicks and conversions.
                Like most websites, our hosts may process technical data such as IP address, browser
                type, device information, pages viewed, and approximate location derived from IP.
              </p>
              <p>
                <span className="font-medium text-white">Product accounts.</span> If your
                organization uses SMPL, we process account information needed to provide the
                service (for example work email for magic-link sign-in, name, organization
                membership, and related authentication records). Customer financial and operational
                data uploaded or connected to SMPL is processed to provide the product under our
                customer agreements.
              </p>
              <p>
                <span className="font-medium text-white">Billing.</span> If you purchase SMPL,
                payment card details are processed by Stripe. We do not store full payment card
                numbers.
              </p>
            </Section>

            <Section id="use" title="3. How we use information">
              <ul className="list-disc space-y-2 pl-5">
                <li>Respond to demo, quote, and sales inquiries</li>
                <li>Operate, secure, and improve our website and product</li>
                <li>Measure and improve advertising performance (including Google Ads)</li>
                <li>Send transactional product email such as sign-in links</li>
                <li>Provide billing and account administration</li>
                <li>Comply with law and enforce our terms</li>
              </ul>
            </Section>

            <Section id="share" title="4. How we share information">
              <p>
                We share information with service providers that help us run our business, including:
              </p>
              <ul className="list-disc space-y-2 pl-5">
                <li>HubSpot — sales CRM for inbound leads</li>
                <li>Google — advertising measurement and appointment scheduling</li>
                <li>Vercel and Railway — application hosting</li>
                <li>Neon — managed database hosting</li>
                <li>Resend — transactional email</li>
                <li>Stripe — payments and subscriptions</li>
                <li>Anthropic — AI commentary features in the product</li>
                <li>Sanity — marketing website content management</li>
              </ul>
              <p>
                We do not sell personal information for money. We may disclose information if
                required by law, to protect rights and security, or in connection with a corporate
                transaction (such as a merger or financing), subject to appropriate safeguards.
              </p>
            </Section>

            <Section id="cookies" title="5. Cookies and advertising">
              <p>
                Marketing pages may use cookies, pixels, or similar technologies from Google Ads to
                understand whether ads led to site visits or form submissions. You can control
                cookies through your browser settings and Google&apos;s ad settings. Blocking cookies
                may limit some measurement features.
              </p>
            </Section>

            <Section id="retention" title="6. Retention">
              <p>
                We keep lead and sales records as long as needed for follow-up and ordinary business
                records. Product and billing data are retained for the life of the customer
                relationship and as needed for legal, security, and accounting purposes. Hosting
                and vendor logs follow each provider&apos;s retention practices unless we configure a
                shorter period.
              </p>
            </Section>

            <Section id="rights" title="7. Your choices and requests">
              <p>
                You can ask us to access, correct, or delete personal information we hold about you,
                or ask questions about this notice, by emailing{" "}
                <a
                  href={`mailto:${SALES_EMAIL}?subject=${encodeURIComponent("Privacy request")}`}
                  className="text-teal-300 hover:text-teal-200"
                >
                  {SALES_EMAIL}
                </a>
                . We may need to verify your request. Some rights may be limited by law or by our
                need to keep records (for example billing or security logs).
              </p>
              <p>
                If you no longer want sales follow-up, say so in your email and we will update our
                CRM accordingly.
              </p>
            </Section>

            <Section id="security" title="8. Security">
              <p>
                We use administrative, technical, and organizational measures appropriate to a B2B
                SaaS product, including encrypted transport (TLS), access controls, and vendor
                hosting controls. No method of transmission or storage is completely secure.
              </p>
            </Section>

            <Section id="children" title="9. Children">
              <p>
                SMPL is a business service and is not directed to children. We do not knowingly
                collect personal information from children under 13.
              </p>
            </Section>

            <Section id="updates" title="10. Changes">
              <p>
                We may update this Privacy Policy from time to time. The &quot;Last updated&quot; date
                at the top will change when we do. Continued use of the site or services after an
                update means you acknowledge the revised notice.
              </p>
            </Section>

            <Section id="contact" title="11. Contact">
              <p>
                SMPL.ai
                <br />
                Email:{" "}
                <a
                  href={`mailto:${SALES_EMAIL}`}
                  className="text-teal-300 hover:text-teal-200"
                >
                  {SALES_EMAIL}
                </a>
                <br />
                Website:{" "}
                <Link href="/" className="text-teal-300 hover:text-teal-200">
                  www.smpl-ai.com
                </Link>
              </p>
            </Section>
          </div>

          <p className="mt-14 border-t border-white/10 pt-6 text-sm text-slate-500">
            This page is a public privacy notice for our website and advertising. Customer product
            data processing may also be governed by a separate agreement or data processing
            addendum. It is not legal advice.
          </p>
        </article>
      </main>
      <LandingFooter />
    </>
  );
}
