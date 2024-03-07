import { Outlet, Link } from "react-router-dom";
import styles from "./Layout.module.css";
import Octo from "../../assets/octo.png"
import { CopyRegular } from "@fluentui/react-icons";
import { Dialog, Stack, TextField, ChoiceGroup, IChoiceGroupOption, Toggle } from "@fluentui/react";
import { useContext, useEffect, useState } from "react";
import { HistoryButton, ShareButton, SettingsButton } from "../../components/common/Button";
import { AppStateContext } from "../../state/AppProvider";
import { CosmosDBStatus, FrontendSettings } from "../../api";

const Layout = () => {
    const [isSharePanelOpen, setIsSharePanelOpen] = useState<boolean>(false);
    const [isSettingsPanelOpen, setIsSettingsPanelOpen] = useState<boolean>(false);
    const [copyClicked, setCopyClicked] = useState<boolean>(false);
    const [copyText, setCopyText] = useState<string>("Copy URL");
    const [saveSettingsClicked, setSaveSettingsClicked] = useState<boolean>(false);
    const [saveSettingsText, setSaveSettingsText] = useState<string>("");
    const appStateContext = useContext(AppStateContext);
    const aiModelChoices: IChoiceGroupOption[] = [
        {key: "gpt-35-turbo", text: "gpt-35-turbo"},
        {key: "gpt-4", text: "gpt-4"}
    ];

    const handleShareClick = () => {
        setIsSharePanelOpen(true);
    };

    const handleSharePanelDismiss = () => {
        setIsSharePanelOpen(false);
        setCopyClicked(false);
        setCopyText("Copy URL");
    };

    const handleSettingsClick = () => {
        setIsSettingsPanelOpen(true);
    };

    const handleSettingsPanelDismiss = () => {
        setIsSettingsPanelOpen(false);
        setSaveSettingsText("");
    };

    const handleCopyClick = () => {
        navigator.clipboard.writeText(window.location.href);
        setCopyClicked(true);
    };

    const handleHistoryClick = () => {
        appStateContext?.dispatch({ type: 'TOGGLE_CHAT_HISTORY' })
    };

    const handleSaveSettingsClick = () => {
        var settings: FrontendSettings;
      //  appStateContext?.state.frontendSettings.header_title = document.getElementById("HeaderTitleTextField")?.innerText;
        appStateContext?.dispatch({ type: 'SET_FRONTEND_SETTINGS', payload: appStateContext?.state.frontendSettings })
        setSaveSettingsClicked(true);
        setSaveSettingsText("Settings saved.");
    };

    useEffect(() => {
        if (copyClicked) {
            setCopyText("Copied URL");
        }
    }, [copyClicked]);

    useEffect(() => {
        if (saveSettingsClicked) {
            setSaveSettingsText("Settings saved.");
        }
    }, [saveSettingsClicked]);

    useEffect(() => { }, [appStateContext?.state.isCosmosDBAvailable.status]);

    useEffect(() => {
        let title = appStateContext?.state.frontendSettings?.page_tab_title ?? "Configure Page Tab Title";
        console.log("Page Tab Title setting: " + appStateContext?.state.frontendSettings?.page_tab_title);
        document.title = title.toString();
    }, [appStateContext?.state.frontendSettings?.page_tab_title]);

    return (
        <div className={styles.layout}>
            <header className={styles.header} role={"banner"}>
                <Stack horizontal verticalAlign="center" horizontalAlign="space-between">
                    <Stack horizontal verticalAlign="center">
                        <img
                            src={Octo}
                            className={styles.headerIcon}
                            aria-hidden="true"
                        />
                        <Link to="/" className={styles.headerTitleContainer}>
                            <h1 className={styles.headerTitle}>{appStateContext?.state.frontendSettings?.header_title}</h1>
                        </Link>
                    </Stack>                    
                    <Stack horizontal tokens={{ childrenGap: 4 }}>
                        {(appStateContext?.state.isCosmosDBAvailable?.status !== CosmosDBStatus.NotConfigured) &&
                            <HistoryButton onClick={handleHistoryClick} text={appStateContext?.state?.isChatHistoryOpen ? "Hide chat history" : "Show chat history"} />
                        }
                        <ShareButton onClick={handleShareClick} />
                        <SettingsButton onClick={handleSettingsClick} />
                    </Stack>
                </Stack>
            </header>
            <Outlet />
            <Dialog
                onDismiss={handleSharePanelDismiss}
                hidden={!isSharePanelOpen}
                styles={{
                    main: [{
                        selectors: {
                            ['@media (min-width: 480px)']: {
                                maxWidth: '600px',
                                background: "#FFFFFF",
                                boxShadow: "0px 14px 28.8px rgba(0, 0, 0, 0.24), 0px 0px 8px rgba(0, 0, 0, 0.2)",
                                borderRadius: "8px",
                                maxHeight: '200px',
                                minHeight: '100px',
                            }
                        }
                    }]
                }}
                dialogContentProps={{
                    title: "Share the web app",
                    showCloseButton: true
                }}
            >
                <Stack horizontal verticalAlign="center" style={{ gap: "8px" }}>
                    <TextField className={styles.urlTextBox} defaultValue={window.location.href} readOnly />
                    <div
                        className={styles.copyButtonContainer}
                        role="button"
                        tabIndex={0}
                        aria-label="Copy"
                        onClick={handleCopyClick}
                        onKeyDown={e => e.key === "Enter" || e.key === " " ? handleCopyClick() : null}
                    >
                        <CopyRegular className={styles.copyButton} />
                        <span className={styles.copyButtonText}>{copyText}</span>
                    </div>
                </Stack>
            </Dialog>
            <Dialog
                onDismiss={handleSettingsPanelDismiss}
                hidden={!isSettingsPanelOpen}
                styles={{
                    main: [{
                        selectors: {
                            ['@media (min-width: 400px)']: {
                                background: "#FFFFFF",
                                boxShadow: "0px 14px 28.8px rgba(0, 0, 0, 0.24), 0px 0px 8px rgba(0, 0, 0, 0.2)",
                                borderRadius: "8px",
                                maxHeight: '600px',
                                minHeight: '400px',
                                maxWidth: '500px',
                                minWidth: '300px',
                                width: '400px',
                                height: '500px',
                            }
                        }
                    }]
                }}
                dialogContentProps={{
                    title: "Settings",
                    showCloseButton: true
                }}
            >
                <Stack verticalAlign="center" style={{ gap: "6px" }}>
                    <Toggle 
                        id="AuthEnabledToggle"
                        label={"Auth Enabled?"} 
                        defaultChecked={appStateContext?.state.frontendSettings?.auth_enabled == "True" ? true : false}>
                    </Toggle>
                    <Toggle 
                        id="FeedbackEnabledToggle"
                        label={"Feedback Enabled?"} 
                        defaultChecked={appStateContext?.state.frontendSettings?.feedback_enabled == "True" ? true : false}>
                    </Toggle>
                    <TextField id="HeaderTitleTextField" label="Header Title" defaultValue={appStateContext?.state.frontendSettings?.header_title!} />
                    <TextField id="PageTabTitleTextField" label="Page Tab Title" defaultValue={appStateContext?.state.frontendSettings?.page_tab_title!} />
                    <ChoiceGroup 
                        id="AIModelNameChoiceGroup"
                        label="AI Model Name"
                        styles={{flexContainer: [{flexDirection: "row"}]}}
                        defaultSelectedKey={appStateContext?.state.frontendSettings?.ai_model_name!}
                        options={aiModelChoices}>
                    </ChoiceGroup>
                </Stack>
                <Stack horizontal verticalAlign="center" style={{ gap: "8px" }}>
                    <span>""</span>
                </Stack>
                <Stack horizontal verticalAlign="center" style={{ gap: "6px" }}>
                    <button tabIndex={0}
                            aria-label="Save"
                            onClick={handleSaveSettingsClick}
                            onKeyDown={e => e.key === "Enter" || e.key === " " ? handleSaveSettingsClick() : null} >
                        Save
                    </button>
                    <button tabIndex={0}
                            aria-label="Close"
                            onClick={handleSettingsPanelDismiss}
                            onKeyDown={e => e.key === "Enter" || e.key === " " ? handleSettingsPanelDismiss() : null} >
                        Close
                    </button>
                </Stack>
                <Stack horizontal verticalAlign="center" style={{ gap: "8px" }}>
                    <span>{saveSettingsText}</span>
                </Stack>
            </Dialog>            
        </div>
    );
};

export default Layout;
