"use client";

import { useEffect, useState } from "react";
import { Alert, Snackbar } from "@mui/material";

export default function Toast({ message, severity, open, onClose }: { message: string; severity: "success" | "error" | "info" | "warning"; open: boolean; onClose: () => void; }) {
  const [visible, setVisible] = useState(open);

  useEffect(() => {
    setVisible(open);
  }, [open]);

  return (
    <Snackbar open={visible} autoHideDuration={4500} onClose={() => { setVisible(false); onClose(); }} anchorOrigin={{ vertical: "bottom", horizontal: "center" }}>
      <Alert onClose={() => { setVisible(false); onClose(); }} severity={severity} sx={{ width: "100%" }}>
        {message}
      </Alert>
    </Snackbar>
  );
}
