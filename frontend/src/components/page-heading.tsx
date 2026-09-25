export function PageHeading({ eyebrow, title, text }: { eyebrow: string; title: string; text?: string }) {
  return (
    <div className="max-w-2xl">
      <p className="eyebrow !text-red">{eyebrow}</p>
      <h1 className="mt-2 font-display text-3xl font-extrabold tracking-tight sm:text-4xl">{title}</h1>
      {text && <p className="mt-3 text-base leading-relaxed text-muted">{text}</p>}
    </div>
  );
}
