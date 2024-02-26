import React, { useContext } from "react";
import ReactDOM from "react-dom/client";
import { HashRouter, Routes, Route } from "react-router-dom";
import { initializeIcons } from "@fluentui/react";
import { AppStateContext } from "./state/AppProvider";

import "./index.css";

import Layout from "./pages/layout/Layout";
import NoPage from "./pages/NoPage";
import Chat from "./pages/chat/Chat";
import { AppStateProvider } from "./state/AppProvider";

initializeIcons();

export default function App() {
    const appStateContext = useContext(AppStateContext)

    document.title = appStateContext?.state.frontendSettings?.page_tab_title ?? "VA Chat Room"; //"test";

    return (
        <AppStateProvider>
            <HashRouter>
                <Routes>
                    <Route path="/" element={<Layout />}>
                        <Route index element={<Chat />} />
                        <Route path="*" element={<NoPage />} />
                    </Route>
                </Routes>
            </HashRouter>
        </AppStateProvider>
    );
}

ReactDOM.createRoot(document.getElementById("root")as HTMLElement).render(
    <React.StrictMode>
        <App />
    </React.StrictMode>
);

