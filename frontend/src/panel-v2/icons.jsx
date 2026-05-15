const I = {};
const mk = (paths, vb = "0 0 24 24") => (props = {}) => (
  <svg viewBox={vb} fill="none" stroke="currentColor" strokeWidth="1.5"
       strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" {...props}>
    {paths}
  </svg>
);

I.Bolt = mk(<path d="M13 3 4 14h7l-1 7 9-11h-7l1-7z"/>);
I.Chat = mk(<><path d="M21 12a8 8 0 0 1-11.6 7.1L4 21l1.9-5.4A8 8 0 1 1 21 12z"/><circle cx="9" cy="12" r=".75" fill="currentColor"/><circle cx="12" cy="12" r=".75" fill="currentColor"/><circle cx="15" cy="12" r=".75" fill="currentColor"/></>);
I.Steps = mk(<><path d="M9 6h11M9 12h11M9 18h11"/><path d="M5 6h.01M5 12h.01M5 18h.01" strokeWidth="2"/></>);
I.Camera = mk(<><rect x="3" y="7" width="18" height="13" rx="2.5"/><path d="M9 7l1.5-2.5h3L15 7"/><circle cx="12" cy="13.5" r="3"/></>);
I.Code = mk(<><path d="M9 8l-4 4 4 4M15 8l4 4-4 4"/></>);
I.Trace = mk(<><path d="M4 7h7M4 12h12M4 17h9"/><circle cx="15" cy="7" r="1.2"/><circle cx="19" cy="12" r="1.2"/><circle cx="16" cy="17" r="1.2"/></>);
I.Plug = mk(<><path d="M9 2v6M15 2v6M7 8h10v3a5 5 0 0 1-10 0V8zM12 16v5"/></>);
I.Settings = mk(<><circle cx="12" cy="12" r="3"/><path d="M12 2v3M12 19v3M5 5l2 2M17 17l2 2M2 12h3M19 12h3M5 19l2-2M17 7l2-2"/></>);
I.Dock = mk(<><rect x="3" y="4" width="18" height="16" rx="2"/><path d="M15 4v16"/></>);
I.DockL = mk(<><rect x="3" y="4" width="18" height="16" rx="2"/><path d="M9 4v16"/></>);
I.DockTop = mk(<><rect x="3" y="4" width="18" height="16" rx="2"/><path d="M3 10h18"/></>);
I.Float = mk(<><rect x="3" y="4" width="14" height="12" rx="2"/><rect x="7" y="8" width="14" height="12" rx="2"/></>);
I.Min = mk(<><path d="M5 12h14"/></>);
I.X = mk(<><path d="M6 6l12 12M18 6 6 18"/></>);
I.Spark = mk(<><circle cx="12" cy="12" r="2" fill="currentColor" stroke="none"/><path d="M12 4v3M12 17v3M4 12h3M17 12h3M6.3 6.3l2 2M15.7 15.7l2 2M6.3 17.7l2-2M15.7 8.3l2-2"/></>);
I.Check = mk(<><path d="m5 12 5 5L20 7"/></>);
I.Play = mk(<><path d="M6 4v16l14-8z" fill="currentColor" stroke="none"/></>);
I.Pause = mk(<><path d="M7 4h4v16H7zM13 4h4v16h-4z" fill="currentColor" stroke="none"/></>);
I.Stop = mk(<><rect x="6" y="6" width="12" height="12" rx="1.5" fill="currentColor" stroke="none"/></>);
I.Retry = mk(<><path d="M21 12a9 9 0 1 1-3-6.7L21 8"/><path d="M21 3v5h-5"/></>);
I.Skip = mk(<><path d="M5 4v16l9-8z" fill="currentColor" stroke="none"/><path d="M19 4v16"/></>);
I.Plus = mk(<><path d="M12 5v14M5 12h14"/></>);
I.Caret = mk(<><path d="m6 9 6 6 6-6"/></>);
I.CaretR = mk(<><path d="m9 6 6 6-6 6"/></>);
I.Send = mk(<><path d="M22 2 11 13M22 2l-7 20-4-9-9-4z"/></>);
I.Paperclip = mk(<><path d="m21 11-9 9a5.5 5.5 0 0 1-7.8-7.8l9-9a4 4 0 0 1 5.7 5.7l-9 9a2.5 2.5 0 0 1-3.5-3.5l8.5-8.5"/></>);
I.Mouse = mk(<><path d="M5 3l7 18 2-8 8-2z" fill="currentColor" stroke="none" opacity=".15"/><path d="M5 3l7 18 2-8 8-2z"/></>);
I.Eye = mk(<><path d="M2 12s4-7 10-7 10 7 10 7-4 7-10 7S2 12 2 12z"/><circle cx="12" cy="12" r="3"/></>);
I.Alert = mk(<><path d="M10.3 3.9 1.8 18a2 2 0 0 0 1.7 3h17a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0z"/><path d="M12 9v4M12 17h.01" strokeLinecap="round"/></>);
I.Info = mk(<><circle cx="12" cy="12" r="9"/><path d="M12 8h.01M11 12h1v5h1"/></>);
I.Copy = mk(<><rect x="8" y="8" width="13" height="13" rx="2"/><path d="M16 8V5a2 2 0 0 0-2-2H5a2 2 0 0 0-2 2v9a2 2 0 0 0 2 2h3"/></>);
I.Download = mk(<><path d="M12 3v13M6 10l6 6 6-6M4 21h16"/></>);
I.Filter = mk(<><path d="M3 5h18l-7 9v6l-4-2v-4z"/></>);
I.Folder = mk(<><path d="M3 7a2 2 0 0 1 2-2h4l2 2h8a2 2 0 0 1 2 2v9a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/></>);
I.Lock = mk(<><rect x="4" y="11" width="16" height="9" rx="2"/><path d="M8 11V7a4 4 0 1 1 8 0v4"/></>);
I.Shield = mk(<><path d="M12 3 4 6v6c0 5 3.5 8 8 9 4.5-1 8-4 8-9V6z"/></>);
I.Target = mk(<><circle cx="12" cy="12" r="8"/><path d="M12 4v3M12 17v3M4 12h3M17 12h3"/><circle cx="12" cy="12" r="1.2" fill="currentColor" stroke="none"/></>);
I.Drag = mk(<><circle cx="9" cy="6" r="1.2" fill="currentColor"/><circle cx="15" cy="6" r="1.2" fill="currentColor"/><circle cx="9" cy="12" r="1.2" fill="currentColor"/><circle cx="15" cy="12" r="1.2" fill="currentColor"/><circle cx="9" cy="18" r="1.2" fill="currentColor"/><circle cx="15" cy="18" r="1.2" fill="currentColor"/></>);
I.More = mk(<><circle cx="6" cy="12" r="1.4" fill="currentColor"/><circle cx="12" cy="12" r="1.4" fill="currentColor"/><circle cx="18" cy="12" r="1.4" fill="currentColor"/></>);
I.Sync = mk(<><path d="M21 12A9 9 0 0 0 6 5.3L3 8"/><path d="M3 12a9 9 0 0 0 15 6.7L21 16"/><path d="M21 3v5h-5M3 21v-5h5"/></>);
I.Repeat = mk(<><path d="M17 3 21 7l-4 4M3 11V9a4 4 0 0 1 4-4h14M7 21l-4-4 4-4M21 13v2a4 4 0 0 1-4 4H3"/></>);
I.Layers = mk(<><path d="M12 3 3 8l9 5 9-5z"/><path d="M3 13l9 5 9-5"/></>);
I.Diff = mk(<><path d="M9 4v12M3 10l6-6 6 6M15 20V8M21 14l-6 6-6-6"/></>);
I.Key = mk(<><circle cx="8" cy="15" r="4"/><path d="m11 12 9-9M16 7l3 3M14 9l2 2"/></>);
I.Branch = mk(<><circle cx="6" cy="6" r="2"/><circle cx="6" cy="18" r="2"/><circle cx="18" cy="9" r="2"/><path d="M6 8v8M16.5 10.5C15 14 11 14 8 14"/></>);
I.Doc = mk(<><path d="M14 3H6a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9zM14 3v6h6M8 13h8M8 17h6"/></>);
I.Globe = mk(<><circle cx="12" cy="12" r="9"/><path d="M3 12h18M12 3a14 14 0 0 1 0 18M12 3a14 14 0 0 0 0 18"/></>);
I.Search = mk(<><circle cx="11" cy="11" r="7"/><path d="m20 20-3.5-3.5"/></>);
export { I };
