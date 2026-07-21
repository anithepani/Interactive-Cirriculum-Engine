"use client";

import { useState } from "react";
import {
  Box,
  Button,
  FormControl,
  InputLabel,
  MenuItem,
  Paper,
  Select,
  TextField,
  Typography,
} from "@mui/material";
import AppLayout from "@/components/layout/AppLayout";
import Toast from "@/components/Toast";
import { authFetch } from "@/lib/auth";

const CATEGORIES = [
  "General",
  "Technical",
  "Billing",
  "Account",
  "Bug Report",
  "Feature Request",
];

export default function SupportPage() {
  const [category, setCategory] = useState("");
  const [subject, setSubject] = useState("");
  const [description, setDescription] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [toastOpen, setToastOpen] = useState(false);
  const [toastMessage, setToastMessage] = useState("");
  const [toastSeverity, setToastSeverity] = useState<"success" | "error">(
    "success"
  );

  const showToast = (message: string, severity: "success" | "error") => {
    setToastMessage(message);
    setToastSeverity(severity);
    setToastOpen(true);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!category || !subject || !description) {
      showToast("Please fill in all fields.", "error");
      return;
    }

    setSubmitting(true);
    try {
      const res = await authFetch("/api/v1/support", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ category, subject, description }),
      });

      if (res.ok) {
        showToast("Support request submitted. We'll get back to you soon!", "success");
        setCategory("");
        setSubject("");
        setDescription("");
      } else {
        const data = await res.json().catch(() => ({}));
        showToast(
          data.detail || data.message || "Failed to submit request.",
          "error"
        );
      }
    } catch {
      showToast("Network error. Please try again.", "error");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <AppLayout>
      <Box sx={{ maxWidth: 720, mx: "auto" }}>
        <Typography variant="h4" sx={{ fontWeight: 700, mb: 1 }}>
          Support
        </Typography>
        <Typography variant="body2" sx={{ color: "text.secondary", mb: 4 }}>
          Need help? Submit a request and our team will respond as soon as possible.
        </Typography>

        <Paper sx={{ p: 4 }} elevation={0} variant="outlined">
          <Box
            component="form"
            onSubmit={handleSubmit}
            sx={{ display: "flex", flexDirection: "column", gap: 3 }}
          >
            <FormControl fullWidth required>
              <InputLabel id="support-category-label">Category</InputLabel>
              <Select
                labelId="support-category-label"
                label="Category"
                value={category}
                onChange={(e) => setCategory(e.target.value as string)}
              >
                {CATEGORIES.map((c) => (
                  <MenuItem key={c} value={c}>
                    {c}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>

            <TextField
              label="Subject"
              value={subject}
              onChange={(e) => setSubject(e.target.value)}
              required
              fullWidth
            />

            <TextField
              label="Description"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              required
              fullWidth
              multiline
              minRows={5}
            />

            <Button
              type="submit"
              variant="contained"
              disabled={submitting}
              sx={{ alignSelf: "flex-start" }}
            >
              {submitting ? "Submitting..." : "Submit Request"}
            </Button>
          </Box>
        </Paper>
      </Box>

      <Toast
        open={toastOpen}
        message={toastMessage}
        severity={toastSeverity}
        onClose={() => setToastOpen(false)}
      />
    </AppLayout>
  );
}
