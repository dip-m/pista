// frontend/src/components/features/FeedbackAdmin.jsx
import React, { useState, useEffect, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import { authService } from "../../services/auth";
import { API_BASE } from "../../config/api";

function FeedbackAdmin({ user }) {
  const navigate = useNavigate();
  const [questions, setQuestions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [editingQuestion, setEditingQuestion] = useState(null);
  const [questionText, setQuestionText] = useState("");
  const [questionType, setQuestionType] = useState("text");
  const [isActive, setIsActive] = useState(true);
  const [options, setOptions] = useState([""]);
  const [showAddForm, setShowAddForm] = useState(false);

  const loadQuestions = useCallback(async () => {
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/admin/feedback/questions`, {
        headers: authService.getAuthHeaders(),
      });
      if (res.ok) {
        const data = await res.json();
        setQuestions(data.questions);
      } else if (res.status === 403) {
        alert("Admin access required");
        navigate("/");
      }
    } catch (err) {
      console.error("Failed to load questions:", err);
    } finally {
      setLoading(false);
    }
  }, [navigate]);

  useEffect(() => {
    loadQuestions();
  }, [loadQuestions]);

  const handleAddOption = () => {
    setOptions([...options, ""]);
  };

  const handleRemoveOption = (index) => {
    setOptions(options.filter((_, i) => i !== index));
  };

  const handleOptionChange = (index, value) => {
    const newOptions = [...options];
    newOptions[index] = value;
    setOptions(newOptions);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!questionText.trim()) {
      alert("Question text is required");
      return;
    }

    if ((questionType === "single_select" || questionType === "multi_select") && options.filter(o => o.trim()).length < 2) {
      alert(`${questionType === "single_select" ? "Single select" : "Multi select"} questions need at least 2 options`);
      return;
    }

    try {
      const filteredOptions = (questionType === "single_select" || questionType === "multi_select")
        ? options.filter(o => o.trim())
        : null;

      if (editingQuestion) {
        // Update existing question
        const res = await fetch(
          `${API_BASE}/admin/feedback/questions/${editingQuestion.id}`,
          {
            method: "PUT",
            headers: {
              ...authService.getAuthHeaders(),
              "Content-Type": "application/json",
            },
            body: JSON.stringify({
              question_text: questionText,
              question_type: questionType,
              is_active: isActive,
              options: filteredOptions,
            }),
          }
        );
        if (res.ok) {
          await loadQuestions();
          resetForm();
        } else {
          alert("Failed to update question");
        }
      } else {
        // Create new question
        const res = await fetch(`${API_BASE}/admin/feedback/questions`, {
          method: "POST",
          headers: {
            ...authService.getAuthHeaders(),
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            question_text: questionText,
            question_type: questionType,
            is_active: isActive,
            options: filteredOptions,
          }),
        });
        if (res.ok) {
          await loadQuestions();
          resetForm();
        } else {
          alert("Failed to create question");
        }
      }
    } catch (err) {
      console.error("Failed to save question:", err);
      alert("Failed to save question");
    }
  };

  const resetForm = () => {
    setEditingQuestion(null);
    setQuestionText("");
    setQuestionType("text");
    setIsActive(true);
    setOptions([""]);
    setShowAddForm(false);
  };

  const handleEdit = (question) => {
    setEditingQuestion(question);
    setQuestionText(question.question_text);
    setQuestionType(question.question_type);
    setIsActive(question.is_active);
    setOptions(question.options && question.options.length > 0 
      ? question.options.map(o => o.text || o)
      : [""]);
    setShowAddForm(true);
  };

  const handleDelete = async (questionId) => {
    if (!window.confirm("Are you sure you want to delete this question?")) return;

    try {
      const res = await fetch(`${API_BASE}/admin/feedback/questions/${questionId}`, {
        method: "DELETE",
        headers: authService.getAuthHeaders(),
      });
      if (res.ok) {
        await loadQuestions();
      } else {
        alert("Failed to delete question");
      }
    } catch (err) {
      console.error("Failed to delete question:", err);
      alert("Failed to delete question");
    }
  };

  return (
    <div className="admin-feedback-page">
      <div className="admin-feedback-container">
        <div className="admin-feedback-header">
          <h2>Admin: Feedback Questions</h2>
          <button className="close-button" onClick={() => navigate("/")}>×</button>
        </div>

        {showAddForm ? (
          <div className="admin-feedback-form">
            <h3>{editingQuestion ? "Edit Question" : "Add New Question"}</h3>
            <form onSubmit={handleSubmit}>
              <div className="form-group">
                <label>Question Text:</label>
                <textarea
                  value={questionText}
                  onChange={(e) => setQuestionText(e.target.value)}
                  rows={3}
                  required
                />
              </div>
              <div className="form-group">
                <label>Question Type:</label>
                <select
                  value={questionType}
                  onChange={(e) => {
                    setQuestionType(e.target.value);
                    if (e.target.value !== "single_select" && e.target.value !== "multi_select") {
                      setOptions([""]);
                    } else if (options.length === 0) {
                      setOptions(["", ""]);
                    }
                  }}
                >
                  <option value="text">Text</option>
                  <option value="single_select">Single Select</option>
                  <option value="multi_select">Multi Select</option>
                </select>
              </div>
              {(questionType === "single_select" || questionType === "multi_select") && (
                <div className="form-group">
                  <label>Options:</label>
                  {options.map((opt, idx) => (
                    <div key={idx} className="option-input">
                      <input
                        type="text"
                        value={opt}
                        onChange={(e) => handleOptionChange(idx, e.target.value)}
                        placeholder={`Option ${idx + 1}`}
                      />
                      {options.length > 1 && (
                        <button
                          type="button"
                          onClick={() => handleRemoveOption(idx)}
                          className="remove-option-btn"
                        >
                          ×
                        </button>
                      )}
                    </div>
                  ))}
                  <button
                    type="button"
                    onClick={handleAddOption}
                    className="add-option-btn"
                  >
                    + Add Option
                  </button>
                </div>
              )}
              <div className="form-group">
                <label>
                  <input
                    type="checkbox"
                    checked={isActive}
                    onChange={(e) => setIsActive(e.target.checked)}
                  />
                  Active
                </label>
              </div>
              <div className="form-actions">
                <button type="submit" className="submit-btn">
                  {editingQuestion ? "Update" : "Create"}
                </button>
                <button type="button" onClick={resetForm} className="cancel-btn">
                  Cancel
                </button>
              </div>
            </form>
          </div>
        ) : (
          <>
            <div className="admin-feedback-actions">
              <button onClick={() => setShowAddForm(true)} className="add-btn">
                + Add Question
              </button>
            </div>
            {loading ? (
              <div className="loading">Loading questions...</div>
            ) : (
              <div className="admin-feedback-list">
                {questions.length === 0 ? (
                  <div className="empty-state">No questions yet. Add one to get started.</div>
                ) : (
                  questions.map((q) => (
                    <div key={q.id} className="feedback-question-item">
                      <div className="question-header">
                        <span className={`question-status ${q.is_active ? "active" : "inactive"}`}>
                          {q.is_active ? "✓" : "○"}
                        </span>
                        <span className="question-type">{q.question_type}</span>
                        <h4>{q.question_text}</h4>
                      </div>
                      {q.options && q.options.length > 0 && (
                        <div className="question-options">
                          Options: {q.options.map(o => o.text || o).join(", ")}
                        </div>
                      )}
                      <div className="question-actions">
                        <button onClick={() => handleEdit(q)} className="edit-btn">
                          Edit
                        </button>
                        <button onClick={() => handleDelete(q.id)} className="delete-btn">
                          Delete
                        </button>
                      </div>
                    </div>
                  ))
                )}
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}

export default FeedbackAdmin;
