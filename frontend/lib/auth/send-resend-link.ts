export async function sendResendMagicLink(params: {
  to: string;
  url: string;
  apiKey: string;
  from: string;
}): Promise<void> {
  const res = await fetch("https://api.resend.com/emails", {
    method: "POST",
    headers: {
      Authorization: `Bearer ${params.apiKey}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      from: params.from,
      to: params.to,
      subject: "Your SMPL sign-in link",
      html: `<div style="font-family:system-ui,sans-serif;max-width:480px;margin:0 auto;padding:24px;color:#0f172a;">
  <p style="font-size:12px;font-weight:600;letter-spacing:0.08em;text-transform:uppercase;color:#14b8a6;margin:0 0 8px;">SMPL customer login</p>
  <h1 style="font-size:22px;font-weight:600;margin:0 0 12px;">Sign in to your workspace</h1>
  <p style="font-size:14px;line-height:1.6;color:#475569;margin:0 0 24px;">Click the button below to open SMPL. This link expires soon and can only be used once.</p>
  <p style="margin:0 0 24px;"><a href="${params.url}" style="display:inline-block;background:#2dd4bf;color:#020617;text-decoration:none;font-size:14px;font-weight:600;padding:12px 24px;border-radius:999px;">Continue to SMPL</a></p>
  <p style="font-size:12px;line-height:1.6;color:#64748b;margin:0;">If you did not request this email, you can ignore it.</p>
</div>`,
      text: `Sign in to SMPL\n\n${params.url}\n\nIf you did not request this, you can ignore this email.`,
    }),
  });

  if (!res.ok) {
    const body = (await res.json().catch(() => null)) as { message?: string } | null;
    const detail = body?.message ?? (await res.text().catch(() => "Unknown Resend error"));
    console.error("[auth] Resend send failed:", res.status, detail);
    throw new Error(`Resend: ${detail}`);
  }

  console.log(`[auth] Magic link emailed via Resend to ${params.to}`);
}
