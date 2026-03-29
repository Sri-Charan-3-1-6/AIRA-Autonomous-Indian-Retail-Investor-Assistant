import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import Header from "./components/Layout/Header";
import Sidebar from "./components/Layout/Sidebar";
import Charts from "./pages/Charts";
import Chat from "./pages/Chat";
import Dashboard from "./pages/Dashboard";
import Portfolio from "./pages/Portfolio";
import Signals from "./pages/Signals";
import Video from "./pages/Video";

const App = () => {
  return (
    <BrowserRouter>
      <div className="relative min-h-screen overflow-x-hidden bg-[var(--bg-primary)] text-[var(--text-primary)]">
        <div className="starfield" />
        <div className="starfield starfield-2" />
        <Sidebar />
        <Header />

        <main className="relative mt-20 min-h-[calc(100vh-80px)] p-4 md:ml-[240px] md:mt-0 md:p-6">
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/portfolio" element={<Portfolio />} />
            <Route path="/signals" element={<Signals />} />
            <Route path="/charts" element={<Charts />} />
            <Route path="/chat" element={<Chat />} />
            <Route path="/video" element={<Video />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  );
};

export default App;
