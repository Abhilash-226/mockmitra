// Input Component with Tailwind CSS
export default function Input({
  type = "text",
  placeholder,
  value,
  onChange,
  error,
  label,
  name,
  required = false,
  className = "",
  ...props
}) {
  const inputClass = error ? "input input-error" : "input";

  return (
    <div className="w-full">
      {label && (
        <label htmlFor={name} className="label">
          {label}
          {required && <span className="text-red-500 ml-1">*</span>}
        </label>
      )}
      <input
        type={type}
        id={name}
        name={name}
        placeholder={placeholder}
        value={value}
        onChange={onChange}
        className={`${inputClass} ${className}`}
        {...props}
      />
      {error && <p className="form-error">{error}</p>}
    </div>
  );
}
