import { motion } from "framer-motion";

const GlowCard = ({ children, className = "", hover = true, ...props }) => (
  <motion.div
    whileHover={hover ? { y: -6, boxShadow: "0 0 30px rgba(0, 212, 255, 0.18)" } : undefined}
    transition={{ duration: 0.24, ease: "easeOut" }}
    className={`glass-card rounded-2xl border border-[var(--border-glow)] p-5 ${className}`}
    {...props}
  >
    {children}
  </motion.div>
);

export default GlowCard;
