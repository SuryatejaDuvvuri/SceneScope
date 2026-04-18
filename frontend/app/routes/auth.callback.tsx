import { useEffect } from "react";
import { useNavigate, useSearchParams } from "react-router";
import { useAuth } from "~/lib/auth";

export default function AuthCallback() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const { setToken } = useAuth();

  useEffect(() => {
    const token = searchParams.get("token");
    const error = searchParams.get("error");

    if (token) {
      setToken(token);
      navigate("/", { replace: true });
    } else {
      console.error("Auth error:", error || "No token received");
      navigate("/", { replace: true });
    }
  }, [searchParams, navigate, setToken]);

  return (
    <div className="min-h-screen bg-space-950 flex items-center justify-center">
      <div className="text-center">
        <div className="holo-spinner mx-auto mb-4" />
        <p className="text-stone-600 font-body">Signing you in...</p>
      </div>
    </div>
  );
}
