import { AnimatePresence, motion } from "framer-motion";

const Modal = ({ open, onClose, title, children }) => (
  <AnimatePresence>
    {open ? (
      <motion.div
        className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4 backdrop-blur-md"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        onClick={onClose}
      >
        <motion.div
          initial={{ y: 24, opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          exit={{ y: 24, opacity: 0 }}
          transition={{ duration: 0.2 }}
          className="glass-card max-h-[90vh] w-full max-w-4xl overflow-auto rounded-2xl border border-[var(--border-glow)] p-6"
          onClick={(e) => e.stopPropagation()}
        >
          <div className="mb-4 flex items-center justify-between">
            <h3 className="text-lg font-semibold text-[var(--text-primary)]">{title}</h3>
            <button onClick={onClose} className="rounded-lg border border-white/10 px-3 py-1 text-sm text-slate-300 hover:border-[var(--neon-blue)]">
              Close
            </button>
          </div>
          {children}
        </motion.div>
      </motion.div>
    ) : null}
  </AnimatePresence>
);

export default Modal;
