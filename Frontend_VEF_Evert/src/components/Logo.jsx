import { Leaf, Sparkle } from "./Icons.jsx";

export default function Logo({ tag, sparkle }) {
  return (
    <span className="logo">
      {sparkle ? <Sparkle /> : <Leaf />}
      <span className="logo-name">Harmony Spa</span>
      {tag && <span className="logo-tag">{tag}</span>}
    </span>
  );
}
